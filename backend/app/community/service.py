"""Contribution persistence and local-only moderation operations."""

from datetime import UTC, datetime
from uuid import UUID

from backend.app.models.operations import ItemSuggestion
from backend.app.schemas.operations import SuggestionCreate
from sqlalchemy import select
from sqlalchemy.orm import Session


def submit_suggestion(session: Session, request: SuggestionCreate) -> ItemSuggestion:
    import re
    from urllib.parse import urlsplit

    match = re.search(r"/item=(\d+)", urlsplit(request.wowhead_url).path)
    assert match is not None
    item_id = int(match.group(1))
    duplicate = session.scalar(
        select(ItemSuggestion)
        .where(
            ItemSuggestion.wowhead_item_id == item_id,
            ItemSuggestion.class_name == request.class_name,
            ItemSuggestion.specialization == request.specialization,
            ItemSuggestion.faction == request.faction,
            ItemSuggestion.character_level == request.character_level,
            ItemSuggestion.equipment_slot == request.equipment_slot,
        )
        .order_by(ItemSuggestion.submitted_at)
    )
    suggestion = ItemSuggestion(
        class_name=request.class_name,
        specialization=request.specialization,
        faction=request.faction,
        character_level=request.character_level,
        equipment_slot=request.equipment_slot,
        suggested_item_name=request.suggested_item_name.strip(),
        wowhead_item_id=item_id,
        submitted_url=request.wowhead_url,
        explanation=request.explanation,
        supporting_evidence=request.supporting_evidence,
        status="pending_review",
        duplicate_of=duplicate.id if duplicate else None,
        duplicate_flagged=duplicate is not None,
    )
    session.add(suggestion)
    session.commit()
    session.refresh(suggestion)
    return suggestion


def review_suggestion(
    session: Session,
    suggestion_id: UUID,
    *,
    decision: str,
    reviewer_identity: str,
    notes: str | None = None,
) -> ItemSuggestion:
    if decision not in {"approved", "rejected", "needs_info"}:
        raise ValueError("decision must be approved, rejected, or needs_info")
    row = session.get(ItemSuggestion, suggestion_id)
    if row is None:
        raise LookupError("Suggestion not found")
    if row.status not in {"pending_review", "needs_info"}:
        raise ValueError("Suggestion already has a final decision")
    row.status = decision
    row.reviewer_identity = reviewer_identity
    row.reviewer_notes = notes
    row.decision_at = datetime.now(UTC)
    session.commit()
    session.refresh(row)
    return row
