"""Deterministic pagination, checkpoint, and hydration tests for full import."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select

from backend.app.ingestion.providers.schemas import ItemResponse
from backend.app.ingestion.providers.thewowdb import ProviderError
from backend.app.ingestion.services.full_catalog_import import (
    create_catalog_job,
    enumerate_full_catalog,
    full_catalog_report,
    hydrate_full_catalog,
)
from backend.app.models.catalog import Item
from backend.app.models.operations import FullCatalogImportJob, FullCatalogProviderItem


def summary(item_id: int) -> dict[str, Any]:
    return {
        "id": item_id,
        "kind": "item",
        "version": "forever",
        "name": f"Fixture {item_id}",
        "quality": "common",
        "item_level": 5,
        "required_level": 2,
    }


def page(number: int, records: list[dict[str, Any]], *, more: bool) -> dict[str, Any]:
    return {
        "version": "forever",
        "kind": "item",
        "build": "fixture-build",
        "page": number,
        "per_page": 100,
        "count": len(records),
        "total": None,
        "has_more": more,
        "links": {
            "next": (
                f"https://thewowdb.com/api/v1/forever/item/?page={number + 1}&per_page=100"
                if more
                else None
            )
        },
        "attribution": {"required": True, "text": "Data from TheWoWDB"},
        "results": records,
    }


def detail(item_id: int) -> dict[str, Any]:
    return {
        "id": item_id,
        "kind": "item",
        "version": "forever",
        "build": "fixture-build",
        "name": f"Fixture {item_id}",
        "quality": "common",
        "item_level": 5,
        "required_level": 2,
        "item_type": "Armor",
        "item_subtype": "Cloth",
        "slot": "Head",
        "armor": None,
        "weapon": None,
        "stats": [],
        "effects": [],
        "classes": [],
        "races": [],
        "factions": [],
        "unique": None,
        "icon_url": None,
        "links": {"html": "https://thewowdb.com/wow-forever/item/fixture"},
        "attribution": {"required": True, "text": "Data from TheWoWDB"},
    }


class FakeProvider:
    name = "TheWoWDB"
    base_url = "https://thewowdb.com/"
    terms_url = "https://thewowdb.com/developers/#terms"
    attribution_text = "Data from TheWoWDB (thewowdb.com)"
    api_root = "https://thewowdb.com/api/v1"

    def __init__(self, pages: dict[int, dict[str, Any]], details: dict[int, Any] | None = None):
        self.pages = pages
        self.details = details or {}
        self.calls: list[int] = []
        self.detail_calls: list[int] = []
        self.current_build = "fixture-build"
        self.fail_page_once: int | None = None
        self.failed_pages: set[int] = set()
        self.etags: dict[int, str | None] = {}
        self.statuses: dict[int, int] = {}

    def list_page_payload(self, page_number: int, per_page: int, *, url=None, **_kwargs):
        assert per_page == 100
        if url:
            page_number = int(url.split("page=")[1].split("&")[0])
        self.calls.append(page_number)
        if page_number == self.fail_page_once and page_number not in self.failed_pages:
            self.failed_pages.add(page_number)
            raise ProviderError("TheWoWDB HTTP 503")
        return self.pages[page_number]

    def get_list_page_etag(self, _page, _per_page):
        return 'W/"page"'

    def get_url_etag(self, _url):
        return 'W/"page"'

    def get_item_detail(self, item_id, **_kwargs):
        self.detail_calls.append(item_id)
        value = self.details.get(item_id, detail(item_id))
        if isinstance(value, Exception):
            self.statuses[item_id] = 404 if "404" in str(value) else 503
            raise value
        self.statuses[item_id] = value.get("_status", 200)
        return ItemResponse.model_validate(value)

    def get_raw_item_payload(self, item_id):
        value = self.details.get(item_id, detail(item_id))
        return {"detail": value if isinstance(value, dict) else None}

    def get_item_etag(self, _item_id):
        return 'W/"detail"'

    def get_item_status(self, item_id):
        return self.statuses.get(item_id, 200)

    def get_item_status_counts(self, item_id):
        status = self.get_item_status(item_id)
        return {str(status): 1} if status is not None else {}

    def get_url_status(self, _url):
        item_id = int(_url.rsplit("/", 1)[-1])
        return self.statuses.get(item_id)


def run_with_app_session(app, fn):
    with app.state.session_factory() as session:
        return fn(session)


def test_full_enumeration_follows_next_and_counts_duplicate_ids(app):
    first_summary = {**summary(701), "provider_extension": {"raw": True}}
    provider = FakeProvider(
        {
            1: page(1, [first_summary, summary(702)], more=True),
            2: page(2, [summary(702), summary(703)], more=False),
        }
    )
    result = run_with_app_session(app, lambda session: enumerate_full_catalog(session, provider))
    assert result["enumeration_complete"] is True
    assert result["pages_completed"] == 2
    assert result["unique_provider_ids"] == 3
    assert result["duplicate_ids"] == 1
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Item)) == 3
        rows = list(session.scalars(select(FullCatalogProviderItem)))
        assert len(rows) == 3
        assert all(row.summary_payload["version"] == "forever" for row in rows)
        assert next(row for row in rows if row.provider_item_id == 701).summary_payload[
            "provider_extension"
        ] == {"raw": True}
        assert all(row.hydration_status == "pending" for row in rows)
        assert all(row.item_id is not None for row in rows)


def test_interrupted_enumeration_resumes_after_last_committed_page(app):
    provider = FakeProvider(
        {1: page(1, [summary(711)], more=True), 2: page(2, [summary(712)], more=False)}
    )
    provider.fail_page_once = 2
    first = run_with_app_session(app, lambda session: enumerate_full_catalog(session, provider))
    assert first["status"] == "partial"
    assert first["last_completed_page"] == 1
    resumed = run_with_app_session(
        app,
        lambda session: enumerate_full_catalog(session, provider, job_id=first["job_id"]),
    )
    assert resumed["enumeration_complete"] is True
    assert provider.calls == [1, 2, 2]
    with app.state.session_factory() as session:
        job = session.get(FullCatalogImportJob, first["job_id"])
        assert job.pages_completed == 2
        assert job.unique_ids == 2


def test_page_200_still_has_more_is_reported_incomplete(app):
    provider = FakeProvider({200: page(200, [summary(719)], more=True)})
    with app.state.session_factory() as session:
        job = create_catalog_job(session, provider)
        job.last_completed_page = 199
        job.pages_completed = 199
        session.commit()
        result = enumerate_full_catalog(session, provider, job_id=job.id)
    assert result["last_completed_page"] == 200
    assert result["enumeration_complete"] is False
    assert result["status"] == "partial"
    assert "ceiling 200" in result["last_error"]


def test_hydration_records_304_404_and_recoverable_failures(app):
    provider = FakeProvider(
        {1: page(1, [summary(721), summary(722), summary(723)], more=False)},
        details={
            721: {**detail(721), "_status": 304},
            722: ProviderError("HTTP 404 Not Found"),
            723: ProviderError("HTTP 503 Service Unavailable"),
        },
    )
    enum = run_with_app_session(app, lambda session: enumerate_full_catalog(session, provider))
    with app.state.session_factory() as session:
        cached = session.scalar(
            select(FullCatalogProviderItem).where(FullCatalogProviderItem.provider_item_id == 721)
        )
        cached.detail_payload = {**detail(721), "name": "Cached unchanged payload"}
        cached.detail_etag = 'W/"detail-v1"'
        session.commit()
    first = run_with_app_session(
        app, lambda session: hydrate_full_catalog(session, provider, job_id=enum["job_id"])
    )
    assert first["status"] == "partial"
    assert first["http_status_counts_this_run"]["304"] == 1
    assert first["http_status_counts_this_run"]["404"] == 1
    assert first["http_status_counts_this_run"]["503"] == 1
    provider.details[723] = detail(723)
    provider.statuses[723] = 200
    resumed = run_with_app_session(
        app, lambda session: hydrate_full_catalog(session, provider, job_id=enum["job_id"])
    )
    assert resumed["status"] == "partial"
    assert resumed["hydration_complete"] is False
    assert resumed["http_status_counts_this_run"]["200"] == 1
    report = run_with_app_session(app, lambda session: full_catalog_report(session, enum["job_id"]))
    assert report["enumeration"]["complete"] is True
    assert report["hydration"]["http_304"] == 1
    assert report["hydration"]["http_404"] == 1
    assert report["local_catalog"]["verification_status_counts"] == {"needs_review": 3}
    detailed_report = run_with_app_session(
        app,
        lambda session: full_catalog_report(session, enum["job_id"], include_remaining_ids=True),
    )
    failed_ids = detailed_report["hydration"]["remaining_or_failed_items"]
    assert [(row["provider_item_id"], row["status"]) for row in failed_ids] == [(722, "not_found")]
    with app.state.session_factory() as session:
        cached = session.scalar(
            select(FullCatalogProviderItem).where(FullCatalogProviderItem.provider_item_id == 721)
        )
        assert cached.detail_payload["name"] == "Cached unchanged payload"
    assert provider.detail_calls == [721, 722, 723, 723]


def test_invalid_summary_is_counted_without_creating_fake_item(app):
    invalid = {"id": "bad", "kind": "item", "version": "forever"}
    provider = FakeProvider({1: page(1, [invalid, summary(731)], more=False)})
    result = run_with_app_session(app, lambda session: enumerate_full_catalog(session, provider))
    assert result["invalid_records"] == 1
    assert result["unique_provider_ids"] == 1
    with app.state.session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Item)) == 1


def test_invalid_summary_with_valid_id_is_preserved_and_hydrated_for_review(app):
    invalid_but_identified = {"id": 741, "kind": "item", "version": "forever"}
    provider = FakeProvider({1: page(1, [invalid_but_identified], more=False)})
    enumeration = run_with_app_session(
        app, lambda session: enumerate_full_catalog(session, provider)
    )
    assert enumeration["invalid_records"] == 1
    assert enumeration["unique_provider_ids"] == 1
    hydration = run_with_app_session(
        app,
        lambda session: hydrate_full_catalog(session, provider, job_id=enumeration["job_id"]),
    )
    assert hydration["hydration_complete"] is True
    with app.state.session_factory() as session:
        observed = session.scalar(
            select(FullCatalogProviderItem).where(FullCatalogProviderItem.provider_item_id == 741)
        )
        item = session.get(Item, observed.item_id)
        assert observed.summary_payload == invalid_but_identified
        assert observed.summary_validation_error is not None
        assert item.name == "Fixture 741"
        assert item.verification_status == "needs_review"


def test_conflicting_detail_is_preserved_without_overwriting_summary_values(app):
    conflicting_detail = {**detail(751), "name": "Different provider detail name"}
    provider = FakeProvider(
        {1: page(1, [summary(751)], more=False)},
        details={751: conflicting_detail},
    )
    enumeration = run_with_app_session(
        app, lambda session: enumerate_full_catalog(session, provider)
    )

    result = run_with_app_session(
        app,
        lambda session: hydrate_full_catalog(session, provider, job_id=enumeration["job_id"]),
    )

    assert result["hydration_complete"] is False
    with app.state.session_factory() as session:
        observation = session.scalar(
            select(FullCatalogProviderItem).where(FullCatalogProviderItem.provider_item_id == 751)
        )
        item = session.get(Item, observation.item_id)
        assert observation.hydration_status == "failed"
        assert observation.detail_payload == conflicting_detail
        assert observation.last_error.startswith("ItemNormalizationError:")
        assert item.name == "Fixture 751"
        assert item.verification_status == "needs_review"
