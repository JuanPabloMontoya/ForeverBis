"""Typed catalog API filters and provenance contracts."""

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.models.catalog import (
    AcquisitionSource,
    DataQualityIssue,
    DataSource,
    GameVersion,
    Item,
    ItemAcquisition,
    ItemStat,
)


def seed_catalog(app) -> tuple[int, int]:
    with Session(app.state.engine) as session, session.begin():
        source = DataSource(
            name="TheWoWDB",
            base_url="https://thewowdb.com/",
            terms_url="https://thewowdb.com/developers/#terms",
            attribution_text="Data from TheWoWDB (thewowdb.com)",
            license_status="permitted_with_attribution",
            last_checked_at=datetime.now(UTC),
        )
        session.add(source)
        session.flush()
        version = GameVersion(
            source_id=source.id,
            game_key="wow_forever",
            build="test-build",
            observed_at=datetime.now(UTC),
            is_current=True,
        )
        session.add(version)
        session.flush()
        staff = Item(
            source_id=source.id,
            source_item_id=35,
            game_version_id=version.id,
            name="Bent Staff",
            quality="common",
            item_level=2,
            required_level=None,
            inventory_type="Two-Hand",
            weapon_type="Staff",
            source_item_url="https://thewowdb.com/wow-forever/item/bent-staff-35/",
            wowhead_url="https://www.wowhead.com/forever/item=35/bent-staff",
            availability_status="unknown",
            verification_status="needs_review",
        )
        sword = Item(
            source_id=source.id,
            source_item_id=25,
            game_version_id=version.id,
            name="Worn Shortsword",
            quality="common",
            item_level=2,
            required_level=1,
            inventory_type="Main Hand",
            weapon_type="One-Handed Sword",
            source_item_url="https://thewowdb.com/wow-forever/item/worn-shortsword-25/",
            wowhead_url="https://www.wowhead.com/forever/item=25/worn-shortsword",
            availability_status="unknown",
            verification_status="provider_reported",
        )
        staff.stats = [ItemStat(stat_type="Strength", value=2)]
        staff.quality_issues = [
            DataQualityIssue(
                field_name="required_level",
                issue_code="list_detail_conflict",
                message="Endpoints disagree; value remains unknown.",
                observed_values={"list": 1, "detail": None},
            )
        ]
        session.add_all([staff, sword])
        session.flush()
        return staff.id, sword.id


def test_items_filter_search_pagination_and_summary(client, app):
    staff_id, _ = seed_catalog(app)

    response = client.get("/api/v1/items?search=staff&quality=COMMON&page=1&page_size=1")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["pages"] == 1
    assert page["items"][0]["id"] == staff_id
    assert page["items"][0]["required_level"] is None
    assert page["items"][0]["quality_issues"][0]["observed_values"] == {
        "list": 1,
        "detail": None,
    }
    assert page["items"][0]["source"]["attribution_text"].startswith("Data from TheWoWDB")

    filtered = client.get("/api/v1/items?min_level=1&max_level=10")
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1

    page_two = client.get("/api/v1/items?page=2&page_size=1&sort_by=name")
    assert page_two.status_code == 200
    assert page_two.json()["total"] == 2
    assert page_two.json()["items"][0]["name"] == "Worn Shortsword"

    summary = client.get("/api/v1/catalog/summary")
    assert summary.status_code == 200
    assert summary.json()["total_items"] == 2
    assert summary.json()["items_by_quality"] == [{"quality": "common", "count": 2}]
    assert summary.json()["active_data_sources"][0]["name"] == "TheWoWDB"


def test_item_detail_returns_stats_provenance_and_external_links(client, app):
    staff_id, _ = seed_catalog(app)
    response = client.get(f"/api/v1/items/{staff_id}")
    assert response.status_code == 200
    detail = response.json()
    assert detail["stats"] == [{"stat_type": "Strength", "value": 2.0}]
    assert detail["game_version"]["build"] == "test-build"
    assert detail["source_item_url"].startswith("https://thewowdb.com/")
    assert detail["wowhead_url"].startswith("https://www.wowhead.com/forever/")
    assert detail["acquisitions"] == []


def test_item_acquisition_provenance_is_returned_when_recorded(client, app):
    staff_id, _ = seed_catalog(app)
    with Session(app.state.engine) as session, session.begin():
        acquisition = AcquisitionSource(
            source_type="quest", name="Synthetic quest fixture", verification_status="needs_review"
        )
        session.add(acquisition)
        session.flush()
        session.add(
            ItemAcquisition(
                item_id=staff_id,
                acquisition_source_id=acquisition.id,
                verification_status="needs_review",
                requirements="Test-only fixture.",
            )
        )
    response = client.get(f"/api/v1/items/{staff_id}")
    assert response.status_code == 200
    assert (
        response.json()["acquisitions"][0]["acquisition_source"]["name"]
        == "Synthetic quest fixture"
    )
    assert response.json()["acquisitions"][0]["verification_status"] == "needs_review"


def test_item_detail_not_found_and_filter_validation(client):
    assert client.get("/api/v1/items/999999").status_code == 404
    invalid = client.get("/api/v1/items?min_level=20&max_level=10")
    assert invalid.status_code == 422
    assert invalid.json()["code"] == "http_error"


def test_catalog_coverage_reports_unknown_levels_and_import_history(client):
    coverage = client.get("/api/v1/catalog/coverage")
    assert coverage.status_code == 200
    assert coverage.json()["total"] == 0
    assert coverage.json()["by_required_level_band"]["unknown"] == 0
    assert coverage.json()["items_with_statistics"] == 0
    assert coverage.json()["items_with_acquisition_sources"] == 0
    assert client.get("/api/v1/catalog/imports?page=1&page_size=10").json() == []
    assert client.get("/api/v1/patches").json() == []
