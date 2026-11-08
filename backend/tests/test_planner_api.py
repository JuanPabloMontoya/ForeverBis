"""Planner aggregation tests use isolated synthetic fixture records only."""

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.catalog import DataSource, GameVersion, Item, ItemStat, ScoringProfile


def add_candidate(
    session: Session,
    source_id: int,
    version_id: int,
    source_item_id: int,
    name: str,
    level: int,
    intellect: int,
) -> Item:
    item = Item(
        source_id=source_id,
        source_item_id=source_item_id,
        game_version_id=version_id,
        name=name,
        quality="uncommon",
        item_level=level,
        required_level=level,
        inventory_type="Head",
        availability_status="available",
        verification_status="verified",
        eligibility_status="verified",
        statistics_status="verified",
        last_validated_at=datetime.now(UTC),
        stats=[ItemStat(stat_type="Intellect", value=Decimal(intellect))],
    )
    session.add(item)
    session.flush()
    return item


def seed_plan(app, *, weights: dict[str, int], provisional: bool = False) -> tuple[int, int]:
    with Session(app.state.engine) as session, session.begin():
        source = DataSource(
            name="Synthetic planner test source",
            base_url="https://example.invalid/",
            terms_url="https://example.invalid/terms",
            attribution_text="Synthetic fixture only",
            license_status="test_only",
        )
        session.add(source)
        session.flush()
        version = GameVersion(
            source_id=source.id,
            game_key="wow_forever_test_fixture",
            build="fixture-only",
            is_current=False,
        )
        profile = ScoringProfile(
            class_name="Mage",
            specialization="Fire",
            role="damage",
            version="fixture-profile-v1",
            active=True,
            provisional=provisional,
            assumptions="Synthetic test-only scoring weights.",
            stat_weights=weights,
            adjustments={},
        )
        session.add_all([version, profile])
        session.flush()
        low = add_candidate(
            session, source.id, version.id, 990001, "Synthetic low-level helm", 1, 3
        )
        high = add_candidate(session, source.id, version.id, 990002, "Synthetic later helm", 10, 9)
        return low.id, high.id


def test_planner_returns_17_explicit_insufficient_or_unavailable_slot_states(client, app):
    with Session(app.state.engine) as session, session.begin():
        source = DataSource(
            name="Synthetic empty source",
            base_url="https://example.invalid/",
            terms_url="https://example.invalid/terms",
            attribution_text="Synthetic fixture only",
            license_status="test_only",
        )
        session.add(source)
        session.flush()
        session.add(
            ScoringProfile(
                class_name="Mage",
                specialization="Fire",
                version="fixture-no-weights",
                active=True,
                provisional=True,
                assumptions="No test weights.",
                stat_weights={},
                adjustments={},
            )
        )
    response = client.get(
        "/api/v1/planner/recommendations",
        params={
            "class_name": "Mage",
            "specialization": "Fire",
            "faction": "Alliance",
            "level": 24,
        },
    )
    assert response.status_code == 200
    plan = response.json()
    assert len(plan["slots"]) == 17
    assert plan["profile_configured"] is False
    assert all(slot["recommendation"] is None for slot in plan["slots"])
    assert next(slot for slot in plan["slots"] if slot["slot"] == "Head")["status"] == "unavailable"
    assert any("no weights" in reason for reason in plan["slots"][0]["explanation"])


def test_planner_uses_level_eligibility_and_same_slot_comparison(client, app):
    low_id, high_id = seed_plan(app, weights={"intellect": 2})
    level_one = client.get(
        "/api/v1/planner/recommendations",
        params={
            "class_name": "Mage",
            "specialization": "Fire",
            "faction": "Alliance",
            "level": 5,
        },
    ).json()
    level_ten = client.get(
        "/api/v1/planner/recommendations",
        params={
            "class_name": "Mage",
            "specialization": "Fire",
            "faction": "Horde",
            "level": 10,
        },
    ).json()
    first = next(slot for slot in level_one["slots"] if slot["slot"] == "Head")
    later = next(slot for slot in level_ten["slots"] if slot["slot"] == "Head")
    assert first["status"] == "recommended"
    assert first["recommendation"]["item"]["id"] == low_id
    assert first["alternatives"] == []
    assert later["recommendation"]["item"]["id"] == high_id
    assert later["alternatives"][0]["item"]["id"] == low_id
    assert later["alternatives"][0]["score_difference"] == 12
    assert later["recommendation"]["result"]["score"] == 18
    assert later["explanation"][1] == "This does not optimize the complete equipment set."


def test_provisional_weights_never_become_a_primary_recommendation(client, app):
    seed_plan(app, weights={"intellect": 2}, provisional=True)
    response = client.get(
        "/api/v1/planner/recommendations",
        params={
            "class_name": "Mage",
            "specialization": "Fire",
            "faction": "Alliance",
            "level": 20,
        },
    )
    assert response.status_code == 200
    head = next(slot for slot in response.json()["slots"] if slot["slot"] == "Head")
    assert head["status"] == "insufficient_data"
    assert head["recommendation"] is None
    assert any("provisional" in reason for reason in head["explanation"])
