"""API contracts for scoring return uncertainty instead of recommendations."""

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.catalog import Item, ScoringProfile

from .test_catalog_api import seed_catalog


def add_profile(app) -> None:
    with Session(app.state.engine) as session, session.begin():
        session.add(
            ScoringProfile(
                class_name="Warrior",
                specialization="Arms",
                role="damage",
                version="test-v1",
                active=True,
                provisional=True,
                assumptions="Synthetic test profile.",
                stat_weights={"strength": 2},
                adjustments={},
            )
        )


def test_scoring_profiles_api_returns_configurable_provisional_profile(client, app):
    add_profile(app)
    response = client.get("/api/v1/scoring-profiles?class_name=warrior&specialization=arms")
    assert response.status_code == 200
    assert response.json()[0]["stat_weights"] == {"strength": 2}
    assert response.json()[0]["provisional"] is True


def test_existing_review_item_never_gets_a_confirmed_score(client, app):
    item_id, _ = seed_catalog(app)
    add_profile(app)
    response = client.post(
        f"/api/v1/items/{item_id}/score",
        json={
            "class_name": "Warrior",
            "specialization": "Arms",
            "faction": "Alliance",
            "level": 20,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "incomplete"
    assert result["score"] is None
    assert result["eligibility"]["status"] == "unknown"


def test_eligibility_endpoint_exposes_unverified_status(client, app):
    item_id, _ = seed_catalog(app)
    response = client.post(
        f"/api/v1/items/{item_id}/eligibility",
        json={
            "class_name": "Warrior",
            "specialization": "Arms",
            "faction": "Alliance",
            "level": 20,
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "unknown"


def test_verified_synthetic_api_item_can_be_scored_and_compared(client, app):
    _, sword_id = seed_catalog(app)
    add_profile(app)
    with Session(app.state.engine) as session, session.begin():
        base = session.scalar(select(Item).where(Item.source_item_id == 25))
        base.name = "Synthetic test one-hand item"
        base.verification_status = "verified"
        base.eligibility_status = "verified"
        base.statistics_status = "verified"
        base.required_level = 1
        base.weapon_type = None
        base.inventory_type = "Main Hand"
        from backend.app.models.catalog import ItemStat

        base.stats.append(ItemStat(stat_type="Strength", value=Decimal(3)))

    response = client.post(
        "/api/v1/items/compare",
        json={
            "class_name": "Warrior",
            "specialization": "Arms",
            "faction": "Alliance",
            "level": 20,
            "slot": "main_hand",
            "item_ids": [sword_id],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ranked"] is True
    assert body["items"][0]["status"] == "provisional"
    assert body["items"][0]["score"] == 6
