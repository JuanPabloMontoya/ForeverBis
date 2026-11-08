"""Bounded, resumable, idempotent TheWoWDB import service."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.ingestion.normalizers.items import (
    FieldIssue,
    ItemNormalizationError,
    NormalizedItem,
    normalize_item,
)
from backend.app.ingestion.providers.base import ItemProvider
from backend.app.ingestion.providers.thewowdb import ProviderError
from backend.app.models.catalog import (
    DataQualityIssue,
    DataSource,
    GameVersion,
    Item,
    ItemEffect,
    ItemRestriction,
    ItemStat,
)
from backend.app.models.operations import CatalogImportSnapshot, ItemDataSnapshot

logger = logging.getLogger(__name__)
MAX_IMPORT_LIMIT = 100


def _issue_dict(issue: FieldIssue, source_item_id: int) -> dict[str, Any]:
    return {
        "source_item_id": source_item_id,
        "field": issue.field_name,
        "code": issue.issue_code,
        "message": issue.message,
        "observed_values": issue.observed_values,
    }


def _upsert_source(session: Session, provider: ItemProvider, checked_at: datetime) -> DataSource:
    source = session.scalar(select(DataSource).where(DataSource.name == provider.name))
    if source is None:
        source = DataSource(
            name=provider.name,
            base_url=provider.base_url,
            terms_url=provider.terms_url,
            attribution_text=provider.attribution_text,
            license_status="permitted_with_attribution",
        )
        session.add(source)
    source.base_url = provider.base_url
    source.terms_url = provider.terms_url
    source.attribution_text = provider.attribution_text
    source.license_status = "permitted_with_attribution"
    source.last_checked_at = checked_at
    session.flush()
    return source


def _get_game_version(
    session: Session, source: DataSource, build: str | None, observed_at: datetime
) -> GameVersion:
    version = session.scalar(
        select(GameVersion).where(
            GameVersion.source_id == source.id,
            GameVersion.game_key == "wow_forever",
            GameVersion.build == build,
        )
    )
    if version is None:
        session.query(GameVersion).filter(
            GameVersion.source_id == source.id,
            GameVersion.game_key == "wow_forever",
            GameVersion.is_current.is_(True),
        ).update({GameVersion.is_current: False}, synchronize_session=False)
        version = GameVersion(
            source_id=source.id,
            game_key="wow_forever",
            build=build,
            observed_at=observed_at,
            is_current=True,
        )
        session.add(version)
        session.flush()
    elif not version.is_current:
        session.query(GameVersion).filter(
            GameVersion.source_id == source.id,
            GameVersion.game_key == "wow_forever",
            GameVersion.is_current.is_(True),
            GameVersion.id != version.id,
        ).update({GameVersion.is_current: False}, synchronize_session=False)
        version.is_current = True
    return version


def _normalized_data(item: NormalizedItem) -> dict[str, Any]:
    def number(value: Decimal | None) -> str | None:
        return _decimal_text(value) if value is not None else None

    return {
        "source_item_id": item.source_item_id,
        "name": item.name,
        "quality": item.quality,
        "item_level": item.item_level,
        "required_level": item.required_level,
        "inventory_type": item.inventory_type,
        "armor_type": item.armor_type,
        "weapon_type": item.weapon_type,
        "unique_equip": item.unique_equip,
        "icon_url": item.icon_url,
        "source_item_url": item.source_item_url,
        "wowhead_url": item.wowhead_url,
        "build": item.build,
        "armor_value": number(item.armor_value),
        "weapon_damage_min": number(item.weapon_damage_min),
        "weapon_damage_max": number(item.weapon_damage_max),
        "weapon_speed": number(item.weapon_speed),
        "stats": [{"type": stat.stat_type, "value": number(stat.value)} for stat in item.stats],
        "effects": [
            {
                "type": effect.effect_type,
                "description": effect.description,
                "spell_id": effect.spell_id,
            }
            for effect in item.effects
        ],
        "restrictions": [
            {"type": restriction.restriction_type, "value": restriction.restriction_value}
            for restriction in item.restrictions
        ],
        "issues": [
            {
                "field": issue.field_name,
                "code": issue.issue_code,
                "message": issue.message,
                "observed_values": issue.observed_values,
            }
            for issue in item.issues
        ],
        "field_provenance": item.field_provenance,
    }


def _hash_payload(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decimal_text(value: Decimal) -> str:
    """Canonicalize scale so PostgreSQL NUMERIC(…,3) does not look like a change."""
    return format(value.normalize(), "f")


def _upsert_item(
    session: Session,
    source: DataSource,
    version: GameVersion,
    normalized: NormalizedItem,
    captured_at: datetime,
    raw_payload: dict[str, Any],
    etag: str | None,
) -> tuple[Item, str, list[str]]:
    item = session.scalar(
        select(Item)
        .where(
            Item.source_id == source.id,
            Item.source_item_id == normalized.source_item_id,
            Item.game_version_id == version.id,
        )
        .with_for_update()
    )
    action = "created" if item is None else "updated"
    before = {}
    if item is None:
        item = Item(
            source_id=source.id,
            source_item_id=normalized.source_item_id,
            game_version_id=version.id,
            name=normalized.name,
            verification_status="needs_review",
            data_quality_status="needs_review",
        )
        session.add(item)
        session.flush()
    else:
        before = {
            "name": item.name,
            "quality": item.quality,
            "item_level": item.item_level,
            "required_level": item.required_level,
            "inventory_type": item.inventory_type,
            "armor_type": item.armor_type,
            "weapon_type": item.weapon_type,
            "unique_equip": item.unique_equip,
            "armor_value": _decimal_text(item.armor_value)
            if item.armor_value is not None
            else None,
            "weapon_damage_min": _decimal_text(item.weapon_damage_min)
            if item.weapon_damage_min is not None
            else None,
            "weapon_damage_max": _decimal_text(item.weapon_damage_max)
            if item.weapon_damage_max is not None
            else None,
            "weapon_speed": _decimal_text(item.weapon_speed)
            if item.weapon_speed is not None
            else None,
            "stats": sorted((row.stat_type, _decimal_text(row.value)) for row in item.stats),
            "effects": sorted(
                (row.effect_type, row.description, row.spell_id) for row in item.effects
            ),
            "restrictions": sorted(
                (row.restriction_type, row.restriction_value) for row in item.restrictions
            ),
        }
        if item.verification_status == "verified" or item.data_quality_status == "verified":
            return item, "skipped_verified", []

    normalized_payload = _normalized_data(normalized)
    normalized_payload["stats"] = sorted(
        (row.stat_type, _decimal_text(row.value)) for row in normalized.stats
    )
    normalized_payload["effects"] = sorted(
        (row.effect_type, row.description, row.spell_id) for row in normalized.effects
    )
    normalized_payload["restrictions"] = sorted(
        (row.restriction_type, row.restriction_value) for row in normalized.restrictions
    )
    comparable = {key: value for key, value in normalized_payload.items() if key in before}
    changed_fields = sorted(key for key, value in comparable.items() if before.get(key) != value)

    item.name = normalized.name
    item.quality = normalized.quality
    item.item_level = normalized.item_level
    item.required_level = normalized.required_level
    item.inventory_type = normalized.inventory_type
    item.armor_type = normalized.armor_type
    item.weapon_type = normalized.weapon_type
    item.unique_equip = normalized.unique_equip
    item.icon_url = normalized.icon_url
    item.source_item_url = normalized.source_item_url
    item.wowhead_url = normalized.wowhead_url
    item.armor_value = normalized.armor_value
    item.weapon_damage_min = normalized.weapon_damage_min
    item.weapon_damage_max = normalized.weapon_damage_max
    item.weapon_speed = normalized.weapon_speed
    item.raw_provider_payload = raw_payload
    item.provider_etag = etag
    item.imported_at = item.imported_at or captured_at
    item.last_successful_refresh_at = captured_at
    item.field_provenance = normalized.field_provenance
    item.availability_status = "unknown"
    item.eligibility_status = "unknown"
    item.statistics_status = "unknown"
    item.data_quality_status = "needs_review" if normalized.issues else "imported"
    item.verification_status = "needs_review" if normalized.issues else "imported"
    item.updated_at = captured_at
    session.flush()

    item.stats.clear()
    item.effects.clear()
    item.restrictions.clear()
    item.quality_issues.clear()
    session.flush()
    item.stats.extend(
        ItemStat(stat_type=row.stat_type, value=row.value) for row in normalized.stats
    )
    item.effects.extend(
        ItemEffect(effect_type=row.effect_type, description=row.description, spell_id=row.spell_id)
        for row in normalized.effects
    )
    item.restrictions.extend(
        ItemRestriction(
            restriction_type=row.restriction_type,
            restriction_value=row.restriction_value,
            verification_status="provider_reported",
        )
        for row in normalized.restrictions
    )
    item.quality_issues.extend(
        DataQualityIssue(
            field_name=issue.field_name,
            issue_code=issue.issue_code,
            message=issue.message,
            observed_values=issue.observed_values,
        )
        for issue in normalized.issues
    )
    session.flush()
    return item, action, changed_fields


def _raw_payload(provider: ItemProvider, item_id: int, summary: Any, detail: Any) -> dict[str, Any]:
    getter = getattr(provider, "get_raw_item_payload", None)
    if callable(getter):
        payload = getter(item_id)
        if isinstance(payload, dict) and payload.get("summary") and payload.get("detail"):
            return payload
    return {
        "summary": summary.model_dump(mode="json"),
        "detail": detail.model_dump(mode="json"),
    }


def _etag(provider: ItemProvider, item_id: int) -> str | None:
    getter = getattr(provider, "get_item_etag", None)
    return getter(item_id) if callable(getter) else None


def _existing_item(
    session: Session, source_id: int, source_item_id: int, build: str | None
) -> Item | None:
    return session.scalar(
        select(Item)
        .join(GameVersion)
        .where(
            Item.source_id == source_id,
            Item.source_item_id == source_item_id,
            GameVersion.game_key == "wow_forever",
            GameVersion.build == build,
        )
    )


def _update_snapshot(
    snapshot: CatalogImportSnapshot, outcome: str, issues: list[FieldIssue]
) -> None:
    if outcome == "created":
        snapshot.imported_count += 1
    elif outcome == "updated":
        snapshot.updated_count += 1
    elif outcome.startswith("skipped"):
        snapshot.skipped_count += 1
    elif outcome == "failed":
        snapshot.failed_count += 1
    if issues:
        snapshot.needs_review_count += 1
    counts = dict(snapshot.quality_counts)
    for issue in issues:
        counts[issue.issue_code] = counts.get(issue.issue_code, 0) + 1
    snapshot.quality_counts = counts


def import_items(
    provider: ItemProvider,
    *,
    limit: int,
    session: Session | None = None,
    dry_run: bool = True,
    per_page: int = 20,
    search: str | None = None,
    resume_snapshot_id: int | None = None,
    refresh: bool = False,
    patch_id: int | None = None,
) -> dict[str, Any]:
    """Import a hard-bounded batch, committing each item and checkpoint independently."""
    if isinstance(limit, bool) or not 1 <= limit <= MAX_IMPORT_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_IMPORT_LIMIT}")
    if not 1 <= per_page <= MAX_IMPORT_LIMIT:
        raise ValueError(f"per_page must be between 1 and {MAX_IMPORT_LIMIT}")
    if search is not None and (not search.strip() or len(search) > 64):
        raise ValueError("search must contain 1 to 64 characters")
    if not dry_run and session is None:
        raise ValueError("A database session is required when dry_run is false")
    if dry_run and resume_snapshot_id is not None:
        raise ValueError("Dry-run cannot resume a persisted snapshot")

    started_at = datetime.now(UTC)
    report: dict[str, Any] = {
        "provider": provider.name,
        "provider_base_url": provider.base_url,
        "terms_url": provider.terms_url,
        "attribution_required": True,
        "build": provider.current_build,
        "captured_at": started_at.isoformat(),
        "dry_run": dry_run,
        "limit": limit,
        "search": search,
        "fetched": 0,
        "retrieved": 0,
        "validated": 0,
        "persisted": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "failed_count": 0,
        "failed_records": [],
        "validation_issue_count": 0,
        "validation_issues": [],
        "validated_records": [],
        "needs_review": 0,
        "snapshot_id": resume_snapshot_id,
        "status": "dry_run" if dry_run else "running",
    }

    snapshot: CatalogImportSnapshot | None = None
    source: DataSource | None = None
    processed_ids: set[int] = set()
    if not dry_run:
        assert session is not None
        source = _upsert_source(session, provider, started_at)
        if resume_snapshot_id is not None:
            snapshot = session.get(CatalogImportSnapshot, resume_snapshot_id)
            if snapshot is None:
                raise ValueError(f"Import snapshot {resume_snapshot_id} does not exist")
            if snapshot.status not in {"running", "partial"}:
                raise ValueError("Only a running or partial snapshot can be resumed")
            if snapshot.source_id != source.id:
                raise ValueError("Snapshot belongs to a different provider")
            if snapshot.search_query != search:
                raise ValueError("Resume search query must match the original snapshot")
            limit = snapshot.requested_limit
            per_page = snapshot.per_page
            processed_ids = set((snapshot.resume_state or {}).get("processed_source_item_ids", []))
        else:
            snapshot = CatalogImportSnapshot(
                source_id=source.id,
                patch_id=patch_id,
                provider_build=provider.current_build,
                search_query=search,
                requested_limit=limit,
                per_page=per_page,
                started_at=started_at,
                status="running",
                resume_state={"processed_source_item_ids": []},
            )
            session.add(snapshot)
            session.commit()
        report["snapshot_id"] = snapshot.id
        report["limit"] = snapshot.requested_limit

    remaining_to_fetch = limit - len(processed_ids)

    try:
        for summary in _iter_summaries(provider, limit, per_page, search):
            if summary.id in processed_ids:
                continue
            if report["fetched"] >= remaining_to_fetch:
                break
            report["fetched"] += 1
            report["retrieved"] = report["fetched"]
            captured_at = datetime.now(UTC)
            detail = None
            normalized = None
            raw_payload = None
            etag = None
            outcome = "failed"
            failure: str | None = None
            try:
                existing = None
                if not dry_run:
                    assert session is not None and source is not None
                    existing = _existing_item(
                        session, source.id, summary.id, provider.current_build
                    )
                    if existing is not None and not refresh:
                        outcome = "skipped"
                        raw_getter = getattr(provider, "get_raw_item_payload", None)
                        raw_summary = (
                            raw_getter(summary.id).get("summary") if callable(raw_getter) else None
                        )
                        raw_payload = {"summary": raw_summary or summary.model_dump(mode="json")}
                        etag = existing.provider_etag
                    elif existing is not None and (
                        existing.verification_status == "verified"
                        or existing.data_quality_status == "verified"
                    ):
                        outcome = "skipped_verified"
                        raw_payload = {"summary": summary.model_dump(mode="json")}
                        etag = existing.provider_etag
                    else:
                        cached = (
                            (existing.raw_provider_payload or {}).get("detail")
                            if existing
                            else None
                        )
                        detail = _fetch_detail(provider, summary.id, existing, cached)
                        normalized = normalize_item(summary, detail)
                        normalized = replace(
                            normalized, build=detail.build or provider.current_build
                        )
                        raw_payload = _raw_payload(provider, summary.id, summary, detail)
                        etag = _etag(provider, summary.id)
                        outcome = "validated"
                else:
                    detail = _fetch_detail(provider, summary.id, None, None)
                    normalized = normalize_item(summary, detail)
                    normalized = replace(normalized, build=detail.build or provider.current_build)
                    outcome = "validated"
                    raw_payload = _raw_payload(provider, summary.id, summary, detail)
                    etag = _etag(provider, summary.id)
                if outcome == "validated":
                    report["validated"] += 1
                    issues = normalized.issues if normalized else []
                    if normalized is not None:
                        report["validated_records"].append(
                            {
                                "source_item_id": normalized.source_item_id,
                                "name": normalized.name,
                                "quality": normalized.quality,
                                "inventory_type": normalized.inventory_type,
                                "item_level": normalized.item_level,
                                "required_level": normalized.required_level,
                                "stat_count": len(normalized.stats),
                                "effect_count": len(normalized.effects),
                                "issue_codes": [issue.issue_code for issue in issues],
                                "verification_status": "needs_review" if issues else "imported",
                            }
                        )
                    report["validation_issues"].extend(
                        _issue_dict(issue, summary.id) for issue in issues
                    )
                    report["validation_issue_count"] = len(report["validation_issues"])
                    if issues:
                        report["needs_review"] += 1
                else:
                    issues = []

                if not dry_run:
                    assert session is not None and source is not None and snapshot is not None
                    if outcome == "validated" and normalized is not None:
                        version = _get_game_version(
                            session,
                            source,
                            normalized.build,
                            captured_at,
                        )
                        # A verified row is immutable to provider refreshes, including a new build.
                        current_verified = session.scalar(
                            select(Item).where(
                                Item.source_id == source.id,
                                Item.source_item_id == summary.id,
                                Item.verification_status == "verified",
                            )
                        )
                        if current_verified is not None:
                            outcome = "skipped_verified"
                        else:
                            item, outcome, changed_fields = _upsert_item(
                                session,
                                source,
                                version,
                                normalized,
                                captured_at,
                                raw_payload or {},
                                etag,
                            )
                            if outcome != "skipped_verified":
                                session.add(
                                    ItemDataSnapshot(
                                        import_snapshot_id=snapshot.id,
                                        item_id=item.id,
                                        source_item_id=summary.id,
                                        outcome=outcome,
                                        content_hash=_hash_payload(raw_payload or {}),
                                        raw_provider_payload=raw_payload,
                                        normalized_payload=_normalized_data(normalized),
                                        changed_fields=changed_fields,
                                        provider_etag=etag,
                                        captured_at=captured_at,
                                    )
                                )
                    if outcome.startswith("skipped"):
                        session.add(
                            ItemDataSnapshot(
                                import_snapshot_id=snapshot.id,
                                item_id=existing.id if existing is not None else None,
                                source_item_id=summary.id,
                                outcome=outcome,
                                content_hash=_hash_payload(raw_payload or {}),
                                raw_provider_payload=raw_payload,
                                normalized_payload=None,
                                changed_fields=[],
                                provider_etag=etag,
                                captured_at=captured_at,
                            )
                        )
                    _update_snapshot(snapshot, outcome, issues)
                    snapshot.fetched_count += 1
                    snapshot.provider_build = provider.current_build
                    snapshot.provider_etag = etag or snapshot.provider_etag
                    processed_ids.add(summary.id)
                    snapshot.resume_state = {
                        "processed_source_item_ids": sorted(processed_ids),
                        "last_source_item_id": summary.id,
                    }
                    snapshot.status = "running"
                    session.commit()
                    report["persisted"] += int(outcome in {"created", "updated"})
                    report["created"] = snapshot.imported_count
                    report["updated"] = snapshot.updated_count
                    report["skipped"] = snapshot.skipped_count
                    report["failed_count"] = snapshot.failed_count
            except (
                ProviderError,
                ItemNormalizationError,
                ValueError,
                TimeoutError,
                OSError,
            ) as exc:
                failure = str(exc)[:450]
                report["failed_records"].append({"source_item_id": summary.id, "reason": failure})
                report["failed_count"] += 1
                logger.warning(
                    "Provider item failed validation/import",
                    extra={"provider": provider.name, "source_item_id": summary.id},
                )
                if not dry_run:
                    assert session is not None and snapshot is not None
                    session.add(
                        ItemDataSnapshot(
                            import_snapshot_id=snapshot.id,
                            source_item_id=summary.id,
                            outcome="failed",
                            content_hash=None,
                            raw_provider_payload=None,
                            normalized_payload=None,
                            changed_fields=[],
                            provider_etag=None,
                            captured_at=captured_at,
                            failure_reason=failure,
                        )
                    )
                    _update_snapshot(snapshot, "failed", [])
                    snapshot.fetched_count += 1
                    processed_ids.add(summary.id)
                    snapshot.resume_state = {
                        "processed_source_item_ids": sorted(processed_ids),
                        "last_source_item_id": summary.id,
                    }
                    session.commit()

        if not dry_run:
            assert session is not None and snapshot is not None
            snapshot.status = "completed"
            snapshot.finished_at = datetime.now(UTC)
            snapshot.error_summary = None
            session.commit()
            report.update(
                status=snapshot.status,
                fetched=snapshot.fetched_count,
                retrieved=snapshot.fetched_count,
                created=snapshot.imported_count,
                updated=snapshot.updated_count,
                skipped=snapshot.skipped_count,
                failed_count=snapshot.failed_count,
                needs_review=snapshot.needs_review_count,
                quality_counts=snapshot.quality_counts,
            )
    except Exception as exc:
        if not dry_run:
            assert session is not None and snapshot is not None
            snapshot.status = "partial" if processed_ids else "failed"
            snapshot.finished_at = datetime.now(UTC)
            snapshot.error_summary = f"{type(exc).__name__}: provider batch interrupted"[:500]
            snapshot.resume_state = {
                "processed_source_item_ids": sorted(processed_ids),
                "last_source_item_id": max(processed_ids) if processed_ids else None,
            }
            session.commit()
            report["status"] = snapshot.status
            report["error"] = snapshot.error_summary
        else:
            report["status"] = "partial"
            report["error"] = f"{type(exc).__name__}: provider batch interrupted"
        logger.error("Catalog import batch interrupted", extra={"provider": provider.name})

    logger.info(
        "Catalog import finished",
        extra={
            "provider": provider.name,
            "snapshot_id": report["snapshot_id"],
            "fetched": report["fetched"],
            "created_count": report["created"],
            "updated_count": report["updated"],
            "failed": report["failed_count"],
        },
    )
    return report


def _fetch_detail(provider: ItemProvider, item_id: int, existing: Item | None, cached: Any) -> Any:
    getter = provider.get_item_detail
    etag = existing.provider_etag if existing is not None else None
    try:
        return getter(item_id, etag=etag, cached_payload=cached)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return getter(item_id)


def _iter_summaries(provider: ItemProvider, limit: int, per_page: int, search: str | None):
    iterator = provider.iter_item_summaries
    if search is None:
        return iterator(limit, per_page=per_page)
    try:
        return iterator(limit, per_page=per_page, search=search)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        raise ValueError("This provider adapter does not support documented name search") from exc
