"""Persistence, idempotence, dry-run, and failure reporting tests."""

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.db.base import Base
from backend.app.ingestion.providers.schemas import ItemListRecord, ItemResponse
from backend.app.ingestion.services.item_importer import import_items
from backend.app.models.catalog import (
    DataQualityIssue,
    DataSource,
    GameVersion,
    Item,
    ItemRestriction,
    ItemStat,
)


class FakeProvider:
    name = "TheWoWDB"
    base_url = "https://thewowdb.com/"
    terms_url = "https://thewowdb.com/developers/#terms"
    attribution_text = "Data from TheWoWDB (thewowdb.com)"
    current_build = "mock-build"

    def __init__(self, summaries, details):
        self.summaries = summaries
        self.details = details

    def iter_item_summaries(self, limit, *, per_page=100):
        yield from self.summaries[:limit]

    def get_item_detail(self, item_id):
        return self.details[item_id]


def records(required_level=None):
    summary = ItemListRecord.model_validate(
        {
            "id": 25,
            "kind": "item",
            "version": "forever",
            "name": "Worn Shortsword",
            "quality": "common",
            "item_level": 2,
            "required_level": 1,
        }
    )
    detail = ItemResponse.model_validate(
        {
            "id": 25,
            "kind": "item",
            "version": "forever",
            "name": "Worn Shortsword",
            "quality": "common",
            "item_level": 2,
            "required_level": required_level,
            "item_type": "Weapon",
            "item_subtype": "One-Handed Sword",
            "slot": "Main Hand",
            "stats": [],
            "effects": [],
            "classes": [],
            "build": "mock-build",
            "links": {"html": "https://thewowdb.com/wow-forever/item/worn-shortsword-25/"},
            "attribution": {
                "required": True,
                "text": "Data from TheWoWDB (thewowdb.com)",
                "url": "https://thewowdb.com/wow-forever/item/worn-shortsword-25/",
            },
        }
    )
    return FakeProvider([summary], {25: detail})


def test_dry_run_validates_and_reports_without_database_writes():
    report = import_items(records(), limit=1, dry_run=True)
    assert report["retrieved"] == report["validated"] == 1
    assert report["persisted"] == 0
    assert report["failed_count"] == 0
    assert report["validation_issue_count"] == 4
    assert report["validation_issues"][0]["field"] == "required_level"


def test_import_persists_provenance_conflict_and_is_idempotent():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = records()
    try:
        with Session(engine) as session:
            first = import_items(provider, limit=1, session=session, dry_run=False)
            second = import_items(provider, limit=1, session=session, dry_run=False)

            item_count = session.scalar(select(func.count(Item.id)))
            source_count = session.scalar(select(func.count(DataSource.id)))
            version_count = session.scalar(select(func.count(GameVersion.id)))
            item = session.scalar(select(Item))
            issue = session.scalar(
                select(DataQualityIssue).where(
                    DataQualityIssue.issue_code == "list_detail_conflict"
                )
            )
            stat_count = session.scalar(select(func.count(ItemStat.id)))
            restriction_count = session.scalar(select(func.count(ItemRestriction.id)))

        assert first["persisted"] == first["created"] == 1
        assert second["persisted"] == second["updated"] == 1
        assert item_count == source_count == version_count == 1
        assert item.required_level is None
        assert item.verification_status == "needs_review"
        assert item.availability_status == "unknown"
        assert issue.observed_values == {"list": 1, "detail": None}
        assert stat_count == restriction_count == 0
    finally:
        engine.dispose()


def test_invalid_detail_is_reported_without_persisting():
    provider = records()
    provider.get_item_detail = lambda _item_id: ItemResponse.model_validate(
        {
            "id": 25,
            "kind": "item",
            "version": "forever",
            "name": "Different Item",
            "build": "mock-build",
        }
    )
    report = import_items(provider, limit=1, dry_run=True)
    assert report["validated"] == 0
    assert report["failed_count"] == 1
    assert report["failed_records"][0]["source_item_id"] == 25
