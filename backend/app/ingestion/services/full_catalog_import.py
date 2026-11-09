"""Resumable full-catalog enumeration and bounded detail hydration."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.ingestion.normalizers.items import (
    FieldIssue,
    ItemNormalizationError,
    normalize_item,
)
from backend.app.ingestion.providers.schemas import ItemListRecord, ItemResponse
from backend.app.ingestion.providers.thewowdb import (
    API_ORIGIN,
    MAX_PAGE_SIZE,
    MAX_PAGES,
    ProviderError,
    TheWoWDBProvider,
)
from backend.app.ingestion.services.item_importer import (
    _get_game_version,
    _upsert_item,
    _upsert_source,
)
from backend.app.models.catalog import DataSource, GameVersion, Item
from backend.app.models.operations import (
    FullCatalogImportJob,
    FullCatalogImportPage,
    FullCatalogProviderItem,
)

logger = logging.getLogger(__name__)
HYDRATION_WORKERS = 2
HYDRATION_BATCH_SIZE = 40


def _valid_page_envelope(payload: dict[str, Any], requested_page: int) -> tuple[bool, str | None]:
    if payload.get("version") != "forever" or payload.get("kind") != "item":
        raise ProviderError("List response was not a Forever item page")
    if payload.get("page") != requested_page:
        raise ProviderError("List response page number did not match the requested page")
    if not isinstance(payload.get("has_more"), bool):
        raise ProviderError("List response omitted a valid has_more flag")
    if not isinstance(payload.get("results"), list):
        raise ProviderError("List response omitted its results array")
    build = payload.get("build")
    if build is not None and not isinstance(build, str):
        raise ProviderError("List response build was not a string")
    return payload["has_more"], build


def _next_page(payload: dict[str, Any], current_page: int) -> tuple[int | None, str | None]:
    links = payload.get("links")
    next_value = links.get("next") if isinstance(links, dict) else None
    if next_value:
        if not isinstance(next_value, str):
            raise ProviderError("List response next link was invalid")
        target = urljoin(API_ORIGIN, next_value)
        TheWoWDBProvider._validate_api_url(target)
        parsed = urlparse(target)
        params = parse_qs(parsed.query)
        try:
            target_page = int(params["page"][0])
            target_size = int(params["per_page"][0])
        except (KeyError, ValueError, IndexError) as exc:
            raise ProviderError("Next link omitted page/per_page values") from exc
        if target_page <= current_page or target_size != MAX_PAGE_SIZE:
            raise ProviderError("Next link did not advance using the requested page size")
        if target_page > MAX_PAGES:
            return target_page, target
        return target_page, target
    return current_page + 1, None


def create_catalog_job(
    session: Session, provider: TheWoWDBProvider, *, per_page: int = MAX_PAGE_SIZE
) -> FullCatalogImportJob:
    if not 1 <= per_page <= MAX_PAGE_SIZE:
        raise ValueError(f"per_page must be between 1 and {MAX_PAGE_SIZE}")
    now = datetime.now(UTC)
    source = _upsert_source(session, provider, now)
    initial_count = session.scalar(select(func.count()).select_from(Item)) or 0
    job = FullCatalogImportJob(
        source_id=source.id,
        provider_version="forever",
        per_page=per_page,
        status="running",
        stage="enumeration",
        started_at=now,
        initial_catalog_count=initial_count,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def _job_or_latest(session: Session, job_id: int | None, *, stage: str) -> FullCatalogImportJob:
    job = (
        session.get(FullCatalogImportJob, job_id)
        if job_id is not None
        else session.scalar(
            select(FullCatalogImportJob)
            .where(
                FullCatalogImportJob.status.in_(["running", "partial", "enumerated"]),
                FullCatalogImportJob.stage == stage,
            )
            .order_by(FullCatalogImportJob.id.desc())
        )
    )
    if job is None:
        raise ValueError("No resumable full-catalog import job was found")
    if job.stage != stage:
        raise ValueError(f"Import job {job.id} is in stage '{job.stage}', not '{stage}'")
    if job.status == "completed" or (job.status == "failed" and job.stage != "enumeration"):
        raise ValueError(f"Import job {job.id} is {job.status} and cannot resume")
    return job


def _item_for_summary(
    session: Session,
    source: DataSource,
    build: str | None,
    summary: ItemListRecord,
    raw_summary: dict[str, Any],
    captured_at: datetime,
) -> tuple[Item, bool]:
    version = _get_game_version(session, source, build, captured_at)
    item = session.scalar(
        select(Item).where(
            Item.source_id == source.id,
            Item.source_item_id == summary.id,
            Item.game_version_id == version.id,
        )
    )
    created = item is None
    if item is None:
        item = Item(
            source_id=source.id,
            source_item_id=summary.id,
            game_version_id=version.id,
            name=summary.name,
            quality=summary.quality,
            item_level=summary.item_level,
            # List/detail required-level disagreement is known; leave the
            # normalized value unknown until the detail is compared.
            required_level=None,
            raw_provider_payload={"summary": raw_summary},
            imported_at=captured_at,
            field_provenance={
                "name": "provider_supplied",
                "quality": "provider_supplied" if summary.quality is not None else "unknown",
                "item_level": "provider_supplied" if summary.item_level is not None else "unknown",
                "required_level": "conflicting_or_unverified",
            },
            data_quality_status="needs_review",
            verification_status="needs_review",
            availability_status="unknown",
            eligibility_status="unknown",
            statistics_status="unknown",
        )
        session.add(item)
        session.flush()
    return item, created


def enumerate_full_catalog(
    session: Session,
    provider: TheWoWDBProvider,
    *,
    job_id: int | None = None,
    per_page: int = MAX_PAGE_SIZE,
) -> dict[str, Any]:
    """Persist every page until the provider confirms has_more=false."""
    job = (
        _job_or_latest(session, job_id, stage="enumeration")
        if job_id
        else create_catalog_job(session, provider, per_page=per_page)
    )
    if job.per_page != per_page and job.last_completed_page == 0:
        job.per_page = per_page
    source = session.get(DataSource, job.source_id)
    assert source is not None
    job.status = "running"
    job.last_error = None
    session.commit()
    counters = {"pages_this_run": 0, "records_this_run": 0, "invalid_this_run": 0}
    page_number = job.last_completed_page + 1
    next_url = job.next_page_url
    try:
        while page_number <= MAX_PAGES:
            requested_url = next_url
            cached_page = session.scalar(
                select(FullCatalogImportPage)
                .join(FullCatalogImportJob, FullCatalogImportJob.id == FullCatalogImportPage.job_id)
                .where(
                    FullCatalogImportJob.source_id == source.id,
                    FullCatalogImportPage.page_number == page_number,
                    FullCatalogImportPage.status == "complete",
                    FullCatalogImportPage.raw_response_payload.is_not(None),
                    FullCatalogImportPage.etag.is_not(None),
                )
                .order_by(FullCatalogImportJob.id.desc())
            )
            payload = provider.list_page_payload(
                page_number,
                job.per_page,
                url=requested_url,
                etag=cached_page.etag if cached_page else None,
                cached_payload=cached_page.raw_response_payload if cached_page else None,
                use_memory_cache=False,
                retain_summaries=False,
            )
            has_more, build = _valid_page_envelope(payload, page_number)
            captured_at = datetime.now(UTC)
            etag = (
                provider.get_url_etag(requested_url)
                if requested_url
                else provider.get_list_page_etag(page_number, job.per_page)
            )
            if build:
                job.provider_build = build
            attribution = payload.get("attribution")
            if isinstance(attribution, dict):
                job.attribution = attribution
            elif job.attribution is None:
                job.attribution = {
                    "required": True,
                    "text": provider.attribution_text,
                    "url": provider.base_url,
                    "terms": provider.terms_url,
                }

            page_row = FullCatalogImportPage(
                job_id=job.id,
                page_number=page_number,
                status="processing",
                provider_build=build,
                etag=etag,
                captured_at=captured_at,
            )
            session.add(page_row)
            session.flush()
            page_unique: set[int] = set()
            page_new_count = 0
            page_duplicates = 0
            page_invalid = 0
            page_fetched = len(payload["results"])
            for raw in payload["results"]:
                try:
                    summary = ItemListRecord.model_validate(raw)
                except (ValidationError, TypeError):
                    page_invalid += 1
                    raw_id = raw.get("id") if isinstance(raw, dict) else None
                    if isinstance(raw_id, int) and not isinstance(raw_id, bool) and raw_id > 0:
                        if raw_id in page_unique:
                            page_duplicates += 1
                            continue
                        page_unique.add(raw_id)
                        provider_item = session.scalar(
                            select(FullCatalogProviderItem).where(
                                FullCatalogProviderItem.source_id == source.id,
                                FullCatalogProviderItem.provider_version == "forever",
                                FullCatalogProviderItem.provider_item_id == raw_id,
                            )
                        )
                        if provider_item is not None and provider_item.job_id == job.id:
                            page_duplicates += 1
                            continue
                        existing_item = None
                        if build is not None:
                            existing_item = session.scalar(
                                select(Item)
                                .join(GameVersion)
                                .where(
                                    Item.source_id == source.id,
                                    Item.source_item_id == raw_id,
                                    GameVersion.game_key == "wow_forever",
                                    GameVersion.build == build,
                                )
                            )
                        raw_copy = raw if isinstance(raw, dict) else {"value": str(raw)}
                        if provider_item is None:
                            provider_item = FullCatalogProviderItem(
                                job_id=job.id,
                                source_id=source.id,
                                provider_version="forever",
                                provider_build=build,
                                provider_item_id=raw_id,
                                item_id=existing_item.id if existing_item else None,
                                source_page=page_number,
                                summary_payload=raw_copy,
                                summary_validation_error="Summary record failed schema validation",
                                summary_etag=etag,
                                summary_captured_at=captured_at,
                                hydration_status="pending",
                            )
                            session.add(provider_item)
                        else:
                            provider_item.job_id = job.id
                            provider_item.provider_build = build
                            provider_item.item_id = existing_item.id if existing_item else None
                            provider_item.source_page = page_number
                            provider_item.summary_payload = raw_copy
                            provider_item.summary_validation_error = (
                                "Summary record failed schema validation"
                            )
                            provider_item.summary_etag = etag
                            provider_item.summary_captured_at = captured_at
                        job.unique_ids += 1
                        page_new_count += 1
                    continue
                if summary.id in page_unique:
                    page_duplicates += 1
                    continue
                page_unique.add(summary.id)
                raw_summary = raw if isinstance(raw, dict) else summary.model_dump(mode="json")
                provider_item = session.scalar(
                    select(FullCatalogProviderItem).where(
                        FullCatalogProviderItem.source_id == source.id,
                        FullCatalogProviderItem.provider_version == "forever",
                        FullCatalogProviderItem.provider_item_id == summary.id,
                    )
                )
                if provider_item is not None and provider_item.job_id == job.id:
                    page_duplicates += 1
                    continue
                item, item_created = _item_for_summary(
                    session, source, build, summary, raw_summary, captured_at
                )
                if item_created:
                    job.catalog_items_created += 1
                else:
                    job.catalog_items_unchanged += 1
                    job.duplicate_prevention_count += 1
                if provider_item is None:
                    provider_item = FullCatalogProviderItem(
                        job_id=job.id,
                        source_id=source.id,
                        provider_version="forever",
                        provider_build=build,
                        provider_item_id=summary.id,
                        item_id=item.id,
                        source_page=page_number,
                        summary_payload=raw_summary,
                        summary_etag=etag,
                        summary_captured_at=captured_at,
                        hydration_status="pending",
                    )
                    session.add(provider_item)
                else:
                    previous_build = provider_item.provider_build
                    provider_item.job_id = job.id
                    provider_item.provider_build = build
                    provider_item.item_id = item.id
                    provider_item.source_page = page_number
                    provider_item.summary_payload = raw_summary
                    provider_item.summary_etag = etag
                    provider_item.summary_captured_at = captured_at
                    if previous_build != build:
                        provider_item.hydration_status = "pending"
                job.unique_ids += 1
                page_new_count += 1

            next_page_number, next_link = (
                _next_page(payload, page_number) if has_more else (None, None)
            )
            page_row.fetched_count = page_fetched
            page_row.unique_count = page_new_count
            page_row.duplicate_count = page_duplicates
            page_row.invalid_count = page_invalid
            page_row.response_metadata = {
                "has_more": has_more,
                "count": payload.get("count"),
                "total": payload.get("total"),
                "next": next_link,
                "attribution": attribution,
            }
            page_row.raw_response_payload = payload
            page_row.status = "complete"
            page_row.completed_at = datetime.now(UTC)
            job.last_completed_page = page_number
            job.pages_completed += 1
            job.summary_records += page_fetched
            job.duplicate_ids += page_duplicates
            job.invalid_records += page_invalid
            job.last_etag = etag or job.last_etag
            job.next_page_url = next_link
            if not has_more:
                job.total_pages = page_number
                job.stage = "hydration"
                job.status = "enumerated"
                job.last_error = None
                job.completed_at = None
                next_url = None
            elif next_page_number is not None and next_page_number > MAX_PAGES:
                job.status = "partial"
                job.last_error = (
                    "Provider still reports more results after documented page ceiling "
                    f"{MAX_PAGES}."
                )
                session.commit()
                counters["pages_this_run"] += 1
                counters["records_this_run"] += page_fetched
                counters["invalid_this_run"] += page_invalid
                return _enumeration_report(job, counters, complete=False)
            else:
                next_url = next_link
                page_number = next_page_number or page_number + 1
            session.commit()
            counters["pages_this_run"] += 1
            counters["records_this_run"] += page_fetched
            counters["invalid_this_run"] += page_invalid
            if not has_more:
                break
        if job.stage == "enumeration" and job.status == "running":
            job.status = "partial"
            job.last_error = (
                f"Reached provider page ceiling {MAX_PAGES} with more results indicated."
            )
            session.commit()
            return _enumeration_report(job, counters, complete=False)
        return _enumeration_report(job, counters, complete=job.status == "enumerated")
    except Exception as exc:
        session.rollback()
        job = session.get(FullCatalogImportJob, job.id)
        if job is not None:
            # Even a failure before page 1 is resumable; the provider may be
            # temporarily unreachable or blocked by the current environment.
            job.status = "partial"
            job.last_error = f"{type(exc).__name__}: {str(exc)[:400]}"
            session.commit()
            return _enumeration_report(job, counters, complete=False)
        raise


def _enumeration_report(
    job: FullCatalogImportJob, counters: dict[str, int], *, complete: bool
) -> dict[str, Any]:
    return {
        "job_id": job.id,
        "stage": job.stage,
        "status": job.status,
        "enumeration_complete": complete,
        "pages_completed": job.pages_completed,
        "last_completed_page": job.last_completed_page,
        "total_pages": job.total_pages,
        "summary_records": job.summary_records,
        "unique_provider_ids": job.unique_ids,
        "duplicate_ids": job.duplicate_ids,
        "invalid_records": job.invalid_records,
        "pages_this_run": counters["pages_this_run"],
        "records_this_run": counters["records_this_run"],
        "next_page_url": job.next_page_url,
        "provider_build": job.provider_build,
        "last_error": job.last_error,
    }


def _detail_fetch(
    provider: TheWoWDBProvider, provider_item: FullCatalogProviderItem
) -> tuple[
    int,
    Any,
    dict[str, Any] | None,
    str | None,
    int | None,
    str | None,
    dict[str, int],
]:
    item_id = provider_item.provider_item_id
    url = f"{provider.api_root}/forever/item/{item_id}"
    try:
        detail = provider.get_item_detail(
            item_id,
            etag=provider_item.detail_etag,
            cached_payload=provider_item.detail_payload,
            cache_response=False,
            retain_raw=True,
        )
        raw = provider.get_raw_item_payload(item_id).get("detail")
        release = getattr(provider, "release_raw_item_payload", None)
        if callable(release):
            release(item_id)
        etag = provider.get_item_etag(item_id) or provider_item.detail_etag
        status = provider.get_item_status(item_id)
        get_counts = getattr(provider, "get_item_status_counts", None)
        attempt_counts = get_counts(item_id) if callable(get_counts) else {}
        release_metadata = getattr(provider, "release_item_metadata", None)
        if callable(release_metadata):
            release_metadata(item_id)
        return (
            item_id,
            detail,
            raw if isinstance(raw, dict) else detail.model_dump(mode="json"),
            etag,
            status,
            None,
            attempt_counts,
        )
    except Exception as exc:
        status = provider.get_url_status(url)
        release = getattr(provider, "release_raw_item_payload", None)
        if callable(release):
            release(item_id)
        get_counts = getattr(provider, "get_item_status_counts", None)
        attempt_counts = get_counts(item_id) if callable(get_counts) else {}
        release_metadata = getattr(provider, "release_item_metadata", None)
        if callable(release_metadata):
            release_metadata(item_id)
        return (
            item_id,
            None,
            None,
            None,
            status,
            f"{type(exc).__name__}: {str(exc)[:400]}",
            attempt_counts,
        )


def hydrate_full_catalog(
    session: Session,
    provider: TheWoWDBProvider,
    *,
    job_id: int | None = None,
    workers: int = HYDRATION_WORKERS,
    retry_not_found: bool = False,
) -> dict[str, Any]:
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    job = _job_or_latest(session, job_id, stage="hydration")
    if job.status not in {"enumerated", "partial", "running"}:
        raise ValueError(f"Import job {job.id} is not ready for hydration")
    source = session.get(DataSource, job.source_id)
    assert source is not None
    job.status = "running"
    job.last_error = None
    session.commit()
    before = _hydration_counts(session, job.id)
    status_counts: dict[str, int] = {}
    failures: list[dict[str, Any]] = []
    attempted_ids: set[int] = set()
    seeded_existing_details = 0
    try:
        while True:
            retry_statuses = ["pending", "failed"]
            if retry_not_found:
                retry_statuses.append("not_found")
            batch = list(
                session.scalars(
                    select(FullCatalogProviderItem)
                    .where(
                        FullCatalogProviderItem.job_id == job.id,
                        FullCatalogProviderItem.hydration_status.in_(retry_statuses),
                        FullCatalogProviderItem.provider_item_id.not_in(attempted_ids)
                        if attempted_ids
                        else True,
                    )
                    .order_by(FullCatalogProviderItem.provider_item_id)
                    .limit(HYDRATION_BATCH_SIZE)
                )
            )
            if not batch:
                break
            pending_batch: list[FullCatalogProviderItem] = []
            for record in batch:
                item = session.get(Item, record.item_id) if record.item_id else None
                raw_payload = item.raw_provider_payload if item is not None else None
                raw_detail = raw_payload.get("detail") if isinstance(raw_payload, dict) else None
                raw_build = raw_detail.get("build") if isinstance(raw_detail, dict) else None
                if (
                    isinstance(raw_detail, dict)
                    and item is not None
                    and item.provider_etag
                    and raw_build == job.provider_build
                ):
                    record.detail_payload = raw_detail
                    record.detail_etag = item.provider_etag
                    record.detail_captured_at = item.last_successful_refresh_at
                    record.hydration_status = "hydrated"
                    record.last_error = None
                    seeded_existing_details += 1
                    session.commit()
                else:
                    pending_batch.append(record)
            if not pending_batch:
                continue
            with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="wowdb-detail") as pool:
                futures = {
                    pool.submit(_detail_fetch, provider, record): record.id
                    for record in pending_batch
                }
                results = [future.result() for future in as_completed(futures)]
            by_provider_id = {result[0]: result[1:] for result in results}
            for record in pending_batch:
                attempted_ids.add(record.provider_item_id)
                _, detail, raw_detail, etag, http_status, error, attempt_counts = (
                    record.provider_item_id,
                    *by_provider_id[record.provider_item_id],
                )
                now = datetime.now(UTC)
                record.detail_attempts += 1
                record.last_attempt_at = now
                record.last_http_status = http_status
                counts_for_record = attempt_counts or {
                    str(http_status) if http_status is not None else "network_or_validation": 1
                }
                status_counts = dict(status_counts)
                cumulative_status_counts = dict(job.http_status_counts or {})
                for key, count in counts_for_record.items():
                    status_counts[key] = status_counts.get(key, 0) + count
                    cumulative_status_counts[key] = cumulative_status_counts.get(key, 0) + count
                job.http_status_counts = cumulative_status_counts
                if detail is None:
                    record.hydration_status = "not_found" if http_status == 404 else "failed"
                    record.last_error = error or "Provider returned no detail record"
                    failures.append(
                        {
                            "provider_item_id": record.provider_item_id,
                            "status": http_status,
                            "error": record.last_error,
                        }
                    )
                    session.commit()
                    continue
                if (
                    http_status == 304
                    and record.detail_payload is not None
                    and record.item_id is not None
                ):
                    record.hydration_status = "hydrated"
                    record.last_error = None
                    session.commit()
                    continue
                typed_detail: ItemResponse | None = None
                try:
                    typed_detail = ItemResponse.model_validate(detail.model_dump(mode="json"))
                    try:
                        summary = ItemListRecord.model_validate(record.summary_payload)
                    except ValidationError:
                        raw_summary = record.summary_payload
                        name = raw_summary.get("name")
                        summary = ItemListRecord.model_validate(
                            {
                                "id": record.provider_item_id,
                                "kind": "item",
                                "version": "forever",
                                "name": name
                                if isinstance(name, str) and name
                                else typed_detail.name,
                                "quality": raw_summary.get("quality", typed_detail.quality),
                                "item_level": raw_summary.get(
                                    "item_level", typed_detail.item_level
                                ),
                                "required_level": raw_summary.get("required_level"),
                                "links": raw_summary.get("links"),
                            }
                        )
                    normalized = normalize_item(summary, typed_detail)
                    if record.summary_validation_error:
                        normalized = replace(
                            normalized,
                            issues=[
                                *normalized.issues,
                                FieldIssue(
                                    "summary",
                                    "invalid_summary_record",
                                    "List summary failed validation; detail values are not treated "
                                    "as summary evidence.",
                                ),
                            ],
                            field_provenance={
                                **normalized.field_provenance,
                                "summary": "invalid",
                            },
                        )
                    normalized = normalized.__class__(
                        **{
                            **normalized.__dict__,
                            "build": typed_detail.build
                            or record.provider_build
                            or job.provider_build,
                        }
                    )
                    version = _get_game_version(session, source, normalized.build, now)
                    existing = session.scalar(
                        select(Item).where(
                            Item.source_id == source.id,
                            Item.source_item_id == record.provider_item_id,
                            Item.game_version_id == version.id,
                        )
                    )
                    if (
                        existing is not None
                        and existing.imported_at is None
                        and existing.raw_provider_payload is None
                    ):
                        # Preserve the three historical seed rows exactly; raw
                        # detail remains available on this provider observation.
                        item = existing
                    else:
                        raw = {
                            "summary": record.summary_payload,
                            "detail": raw_detail or typed_detail.model_dump(mode="json"),
                        }
                        item, action, _changed = _upsert_item(
                            session,
                            source,
                            version,
                            normalized,
                            now,
                            raw,
                            etag,
                        )
                        if action == "updated":
                            job.catalog_items_updated += 1
                        elif action.startswith("skipped"):
                            job.catalog_items_unchanged += 1
                    record.item_id = item.id
                    record.detail_payload = raw_detail or typed_detail.model_dump(mode="json")
                    record.detail_etag = etag or record.detail_etag
                    if http_status != 304:
                        record.detail_captured_at = now
                    record.hydration_status = "hydrated"
                    record.last_error = None
                    session.commit()
                except (ValidationError, ItemNormalizationError, ValueError) as exc:
                    record.hydration_status = "failed"
                    # Keep the provider's exact detail response even when it conflicts
                    # with the summary or fails normalization. The raw observation is
                    # needed for later review and must not be replaced by normalized data.
                    record.detail_payload = raw_detail or (
                        typed_detail.model_dump(mode="json") if typed_detail is not None else None
                    )
                    record.detail_etag = etag or record.detail_etag
                    record.detail_captured_at = now
                    record.last_error = f"{type(exc).__name__}: {str(exc)[:400]}"
                    failures.append(
                        {
                            "provider_item_id": record.provider_item_id,
                            "status": http_status,
                            "error": record.last_error,
                        }
                    )
                    session.commit()
        job.stage = "hydration"
        remaining = (
            session.scalar(
                select(func.count())
                .select_from(FullCatalogProviderItem)
                .where(
                    FullCatalogProviderItem.job_id == job.id,
                    FullCatalogProviderItem.hydration_status.in_(["pending", "failed"]),
                )
            )
            or 0
        )
        not_found_total = _hydration_counts(session, job.id).get("not_found", 0)
        incomplete = remaining + not_found_total
        job.status = "partial" if incomplete else "completed"
        job.completed_at = datetime.now(UTC) if not incomplete else None
        job.last_error = (
            f"{remaining} retryable details and {not_found_total} HTTP 404 details remain."
            if incomplete
            else None
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        job = session.get(FullCatalogImportJob, job.id)
        job.status = "partial"
        job.last_error = f"{type(exc).__name__}: {str(exc)[:400]}"
        session.commit()
    after = _hydration_counts(session, job.id)
    return {
        "job_id": job.id,
        "stage": job.stage,
        "status": job.status,
        "enumeration_complete": job.total_pages is not None and job.stage == "hydration",
        "hydration_complete": job.status == "completed",
        "discovered_ids": job.unique_ids,
        "attempted_this_run": sum(status_counts.values()),
        "seeded_from_existing_raw_details": seeded_existing_details,
        "http_status_counts_this_run": status_counts,
        "hydration_counts_before": before,
        "hydration_counts_after": after,
        "pending_or_failed": after.get("pending", 0) + after.get("failed", 0),
        "not_found": after.get("not_found", 0),
        "failures": failures,
        "last_error": job.last_error,
    }


def _hydration_counts(session: Session, job_id: int) -> dict[str, int]:
    rows = session.execute(
        select(FullCatalogProviderItem.hydration_status, func.count())
        .where(FullCatalogProviderItem.job_id == job_id)
        .group_by(FullCatalogProviderItem.hydration_status)
    ).all()
    return {status: count for status, count in rows}


def full_catalog_report(
    session: Session, job_id: int, *, include_remaining_ids: bool = False
) -> dict[str, Any]:
    job = session.get(FullCatalogImportJob, job_id)
    if job is None:
        raise ValueError(f"Full-catalog job {job_id} was not found")
    hydration = _hydration_counts(session, job.id)
    pages = list(
        session.execute(
            select(FullCatalogImportPage.page_number, FullCatalogImportPage.status)
            .where(FullCatalogImportPage.job_id == job.id)
            .order_by(FullCatalogImportPage.page_number)
        )
    )
    item_counts = session.execute(
        select(Item.verification_status, func.count())
        .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
        .where(FullCatalogProviderItem.job_id == job.id)
        .group_by(Item.verification_status)
    ).all()
    slot_counts = session.execute(
        select(Item.inventory_type, func.count())
        .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
        .where(FullCatalogProviderItem.job_id == job.id)
        .group_by(Item.inventory_type)
    ).all()
    level_rows = list(
        session.scalars(
            select(Item.required_level)
            .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
            .where(FullCatalogProviderItem.job_id == job.id)
        )
    )
    levels = {
        "1-10": sum(value is not None and 1 <= value <= 10 for value in level_rows),
        "11-20": sum(value is not None and 11 <= value <= 20 for value in level_rows),
        "21-30": sum(value is not None and 21 <= value <= 30 for value in level_rows),
        "31-40": sum(value is not None and 31 <= value <= 40 for value in level_rows),
        "41-50": sum(value is not None and 41 <= value <= 50 for value in level_rows),
        "51-60": sum(value is not None and 51 <= value <= 60 for value in level_rows),
        "unknown": sum(value is None for value in level_rows),
    }
    total_rows = (
        session.scalar(
            select(func.count())
            .select_from(FullCatalogProviderItem)
            .where(FullCatalogProviderItem.job_id == job.id)
        )
        or 0
    )
    raw_count = (
        session.scalar(
            select(func.count())
            .select_from(FullCatalogProviderItem)
            .where(
                FullCatalogProviderItem.job_id == job.id,
                FullCatalogProviderItem.summary_payload.is_not(None),
            )
        )
        or 0
    )
    detailed_count = (
        session.scalar(
            select(func.count())
            .select_from(FullCatalogProviderItem)
            .where(
                FullCatalogProviderItem.job_id == job.id,
                FullCatalogProviderItem.detail_payload.is_not(None),
            )
        )
        or 0
    )
    remaining_rows = []
    if include_remaining_ids:
        remaining_rows = session.execute(
            select(
                FullCatalogProviderItem.provider_item_id,
                FullCatalogProviderItem.hydration_status,
                FullCatalogProviderItem.detail_attempts,
                FullCatalogProviderItem.last_error,
            )
            .where(
                FullCatalogProviderItem.job_id == job.id,
                FullCatalogProviderItem.hydration_status != "hydrated",
            )
            .order_by(FullCatalogProviderItem.provider_item_id)
        ).all()
    stats_count = (
        session.scalar(
            select(func.count(func.distinct(Item.id)))
            .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
            .where(FullCatalogProviderItem.job_id == job.id)
        )
        or 0
    )
    stats_items = (
        session.scalar(
            select(func.count(func.distinct(Item.id)))
            .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
            .where(
                FullCatalogProviderItem.job_id == job.id,
                Item.stats.any(),
            )
        )
        or 0
    )
    restriction_items = (
        session.scalar(
            select(func.count(func.distinct(Item.id)))
            .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
            .where(
                FullCatalogProviderItem.job_id == job.id,
                Item.restrictions.any(),
            )
        )
        or 0
    )
    acquisition_items = (
        session.scalar(
            select(func.count(func.distinct(Item.id)))
            .join(FullCatalogProviderItem, FullCatalogProviderItem.item_id == Item.id)
            .where(
                FullCatalogProviderItem.job_id == job.id,
                Item.acquisitions.any(),
            )
        )
        or 0
    )
    build_rows = session.execute(
        select(FullCatalogProviderItem.provider_build, func.count())
        .where(FullCatalogProviderItem.job_id == job.id)
        .group_by(FullCatalogProviderItem.provider_build)
    ).all()
    return {
        "job_id": job.id,
        "provider": "TheWoWDB",
        "provider_version": job.provider_version,
        "provider_build": job.provider_build,
        "attribution": job.attribution,
        "status": job.status,
        "stage": job.stage,
        "enumeration": {
            "complete": job.total_pages is not None,
            "pages_discovered": job.total_pages,
            "pages_completed": job.pages_completed,
            "pages_remaining": None
            if job.total_pages is None
            else max(0, job.total_pages - job.pages_completed),
            "page_statuses": [{"page": number, "status": status} for number, status in pages],
            "summary_records_fetched": job.summary_records,
            "unique_provider_ids": job.unique_ids,
            "duplicate_ids": job.duplicate_ids,
            "invalid_records": job.invalid_records,
            "last_completed_page": job.last_completed_page,
        },
        "hydration": {
            "complete": job.status == "completed",
            "total_ids": total_rows,
            "successful_detail_responses": sum(
                count
                for code, count in job.http_status_counts.items()
                if code.isdigit() and 200 <= int(code) < 300 and int(code) != 304
            ),
            "hydrated_records_including_cached": hydration.get("hydrated", 0),
            "http_304": job.http_status_counts.get("304", 0),
            "http_404": job.http_status_counts.get("404", 0),
            "http_404_item_ids": hydration.get("not_found", 0),
            "http_429": job.http_status_counts.get("429", 0),
            "http_5xx": sum(
                value for key, value in job.http_status_counts.items() if key.startswith("5")
            ),
            "network_failures": job.http_status_counts.get("network_or_validation", 0),
            "pending_ids": hydration.get("pending", 0),
            "failed_ids": hydration.get("failed", 0),
            "not_found_ids": hydration.get("not_found", 0),
            "remaining_or_failed_items": [
                {
                    "provider_item_id": item_id,
                    "status": status,
                    "attempts": attempts,
                    "last_error": error,
                }
                for item_id, status, attempts, error in remaining_rows
            ],
        },
        "local_catalog": {
            "items_in_job": total_rows,
            "total_records_before": job.initial_catalog_count,
            "total_records_after": session.scalar(select(func.count()).select_from(Item)) or 0,
            "new_records": job.catalog_items_created,
            "updated_records": job.catalog_items_updated,
            "unchanged_records": job.catalog_items_unchanged,
            "duplicate_prevention_count": job.duplicate_prevention_count,
            "verification_status_counts": {status: count for status, count in item_counts},
            "equipment_slot_counts": {slot or "unknown": count for slot, count in slot_counts},
            "required_level_ranges": levels,
            "missing_required_level": levels["unknown"],
            "items_with_statistics": stats_items,
            "missing_statistics": max(0, stats_count - stats_items),
            "items_with_restrictions": restriction_items,
            "missing_restrictions": max(0, stats_count - restriction_items),
            "acquisition_information": acquisition_items,
            "raw_summary_payloads": raw_count,
            "raw_detail_payloads": detailed_count,
            "provider_build": job.provider_build,
            "records_by_provider_build": {build or "unknown": count for build, count in build_rows},
        },
        "last_error": job.last_error,
    }
