"""Contribution tests use isolated SQLite and synthetic submissions only."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.community.service import review_suggestion
from backend.app.models.catalog import Item, ScoringProfile
from backend.app.models.operations import ItemSuggestion


def payload(url: str = "https://www.wowhead.com/forever/item=900001/test-item") -> dict:
    return {
        "class_name": "Mage",
        "specialization": "Fire",
        "faction": "Alliance",
        "character_level": 20,
        "equipment_slot": "head",
        "suggested_item_name": "Test item",
        "wowhead_url": url,
        "explanation": "Synthetic test suggestion",
    }


def add_profile(app) -> None:
    with Session(app.state.engine) as session:
        session.add(
            ScoringProfile(
                class_name="Mage",
                specialization="Fire",
                version="test-only",
                active=True,
                provisional=True,
                assumptions="Synthetic test fixture.",
                stat_weights={},
                adjustments={},
            )
        )
        session.commit()


def test_suggestion_is_pending_and_duplicate_is_flagged(client: TestClient, app):
    add_profile(app)
    first = client.post("/api/v1/suggestions", json=payload())
    second = client.post("/api/v1/suggestions", json=payload())

    assert first.status_code == 201
    assert first.json()["status"] == "pending_review"
    assert UUID(first.json()["id"])
    assert second.status_code == 201
    assert second.json()["duplicate_flagged"] is True
    assert second.json()["id"] != first.json()["id"]
    assert (
        client.get(f"/api/v1/suggestions/{second.json()['id']}").json()["status"]
        == "pending_review"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://www.wowhead.com/forever/item=1/test",
        "https://wowhead.com/forever/item=1/test",
        "https://evil.example/forever/item=1/test",
        "https://www.wowhead.com/classic/item=1/test",
        "https://www.wowhead.com/forever/item=1/test?x=1",
    ],
)
def test_invalid_wowhead_urls_are_rejected(client: TestClient, url: str):
    assert client.post("/api/v1/suggestions", json=payload(url)).status_code == 422


def test_public_administrative_review_endpoint_is_not_exposed(client: TestClient, app):
    add_profile(app)
    receipt = client.post("/api/v1/suggestions", json=payload()).json()
    assert client.get("/api/v1/admin/suggestions").status_code == 404
    assert client.post(f"/api/v1/admin/suggestions/{receipt['id']}/approve").status_code == 404


def test_operator_approval_never_verifies_or_creates_item(client: TestClient, app):
    add_profile(app)
    receipt = client.post("/api/v1/suggestions", json=payload()).json()
    with Session(app.state.engine) as session:
        reviewed = review_suggestion(
            session,
            UUID(receipt["id"]),
            decision="approved",
            reviewer_identity="local-test-operator",
            notes="Reviewed manually",
        )
        assert reviewed.status == "approved"
        assert reviewed.reviewer_identity == "local-test-operator"
        assert session.query(Item).count() == 0
        assert session.query(ItemSuggestion).count() == 1
