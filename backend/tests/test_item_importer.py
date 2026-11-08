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
from backend.app.models.operations import ItemDataSnapshot


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
        assert second["persisted"] == 0
        assert second["skipped"] == 1
        assert item_count == source_count == version_count == 1
        assert item.required_level is None
        assert item.verification_status == "needs_review"
        assert item.raw_provider_payload["detail"]["id"] == 25
        assert item.field_provenance["required_level"] == "conflicting"
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


def test_partial_import_resumes_without_duplicate_item_rows():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = records()
    second_summary = ItemListRecord.model_validate(
        {
            "id": 26,
            "kind": "item",
            "version": "forever",
            "name": "Second Test Sword",
            "quality": "common",
            "item_level": 2,
            "required_level": None,
        }
    )
    second_detail = ItemResponse.model_validate(
        {
            "id": 26,
            "kind": "item",
            "version": "forever",
            "name": "Second Test Sword",
            "quality": "common",
            "item_level": 2,
            "required_level": None,
            "item_type": "Weapon",
            "item_subtype": "One-Handed Sword",
            "slot": "Main Hand",
            "stats": [],
            "effects": [],
            "classes": [],
            "build": "mock-build",
        }
    )
    provider.details[26] = second_detail
    original_iterator = provider.iter_item_summaries
    interrupted = True

    def interrupt_once(limit, *, per_page=100):
        nonlocal interrupted
        if interrupted:
            interrupted = False
            yield provider.summaries[0]
            raise RuntimeError("simulated interruption")
        yield provider.summaries[0]
        yield second_summary

    provider.iter_item_summaries = interrupt_once
    try:
        with Session(engine) as session:
            partial = import_items(provider, limit=2, session=session, dry_run=False)
            resumed = import_items(
                provider,
                limit=2,
                session=session,
                dry_run=False,
                resume_snapshot_id=partial["snapshot_id"],
            )
            assert partial["status"] == "partial"
            assert resumed["status"] == "completed"
            assert resumed["created"] == 2
            assert session.scalar(select(func.count(Item.id))) == 2
    finally:
        provider.iter_item_summaries = original_iterator
        engine.dispose()


def test_limit_is_not_reduced_twice_during_a_batch():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    seed = records()
    summaries = []
    details = {}
    for item_id in (25, 26, 27):
        summary = ItemListRecord.model_validate(
            {
                "id": item_id,
                "kind": "item",
                "version": "forever",
                "name": f"Mock Sword {item_id}",
                "quality": "common",
                "item_level": 2,
                "required_level": 1,
            }
        )
        summaries.append(summary)
        details[item_id] = ItemResponse.model_validate(
            {
                "id": item_id,
                "kind": "item",
                "version": "forever",
                "name": summary.name,
                "quality": "common",
                "item_level": 2,
                "required_level": 1,
                "item_type": "Weapon",
                "item_subtype": "One-Handed Sword",
                "slot": "Main Hand",
                "stats": [{"type": "Strength", "value": 1}],
                "effects": [{"type": "equip", "description": "Test effect"}],
                "classes": ["Warrior"],
                "build": "mock-build",
            }
        )
    seed.summaries = summaries
    seed.details = details
    with Session(engine) as session:
        report = import_items(seed, limit=3, session=session, dry_run=False)
        assert report["fetched"] == 3
        assert report["created"] == 3
        assert report["status"] == "completed"
    engine.dispose()


def test_refresh_records_field_changes_in_immutable_item_snapshot():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    provider = records()
    provider.details[25] = ItemResponse.model_validate(
        {
            "id": 25,
            "kind": "item",
            "version": "forever",
            "name": "Worn Shortsword",
            "quality": "common",
            "item_level": 2,
            "required_level": 1,
            "item_type": "Weapon",
            "item_subtype": "One-Handed Sword",
            "slot": "Main Hand",
            "weapon": {"damage_min": 2, "damage_max": 4, "speed": 2.2},
            "stats": [{"type": "Strength", "value": 1}],
            "effects": [{"type": "equip", "description": "Fixture effect"}],
            "classes": ["Warrior"],
            "build": "mock-build",
        }
    )
    with Session(engine) as session:
        first = import_items(provider, limit=1, session=session, dry_run=False)
        provider.details[25] = ItemResponse.model_validate(
            {
                "id": 25,
                "kind": "item",
                "version": "forever",
                "name": "Worn Shortsword",
                "quality": "common",
                "item_level": 2,
                "required_level": 1,
                "item_type": "Weapon",
                "item_subtype": "One-Handed Sword",
                "slot": "Main Hand",
                "weapon": {"damage_min": 2, "damage_max": 4, "speed": 2.2},
                "stats": [{"type": "Strength", "value": 2}],
                "effects": [{"type": "equip", "description": "Fixture effect"}],
                "classes": ["Warrior"],
                "build": "mock-build",
            }
        )
        second = import_items(provider, limit=1, session=session, dry_run=False, refresh=True)
        snapshot = session.scalar(
            select(ItemDataSnapshot).where(
                ItemDataSnapshot.import_snapshot_id == second["snapshot_id"]
            )
        )
        assert first["created"] == 1
        assert second["updated"] == 1
        assert snapshot.changed_fields == ["stats"]
    engine.dispose()
