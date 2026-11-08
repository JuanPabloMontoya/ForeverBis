"""Read-only profile, eligibility, and item score endpoints."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.catalog.queries import item_load_options
from backend.app.db.session import get_session
from backend.app.models.catalog import ClassCapabilityProfile, Item, ScoringProfile
from backend.app.recommendations.domain import (
    Character,
    ClassCapabilities,
    EquipmentItem,
    Restriction,
)
from backend.app.recommendations.domain import (
    ScoringProfile as DomainProfile,
)
from backend.app.recommendations.eligibility import canonical_slot, evaluate_eligibility
from backend.app.recommendations.scoring import compare_items, score_item
from backend.app.schemas.catalog import CatalogItemRead
from backend.app.schemas.planner import (
    GearPlanResponse,
    PlannerCandidate,
    PlannerCharacter,
    PlannerSlot,
)
from backend.app.schemas.scoring import (
    CharacterRequest,
    EligibilityRead,
    ItemCheckRequest,
    ItemCompareRequest,
    ItemComparisonRead,
    ScoreRead,
    ScoringProfileRead,
)

router = APIRouter(tags=["scoring foundation"])
SessionDep = Annotated[Session, Depends(get_session)]

PLANNER_SLOTS = (
    ("head", "Head"),
    ("neck", "Neck"),
    ("shoulders", "Shoulders"),
    ("back", "Back"),
    ("chest", "Chest"),
    ("wrist", "Wrist"),
    ("hands", "Hands"),
    ("waist", "Waist"),
    ("legs", "Legs"),
    ("feet", "Feet"),
    ("ring_1", "Ring 1"),
    ("ring_2", "Ring 2"),
    ("trinket_1", "Trinket 1"),
    ("trinket_2", "Trinket 2"),
    ("main_hand", "Main Hand"),
    ("off_hand", "Off Hand"),
    ("ranged", "Ranged"),
)

_SLOT_FAMILY = {
    "ring_1": "ring",
    "ring_2": "ring",
    "trinket_1": "trinket",
    "trinket_2": "trinket",
}


def _profile_row(session: Session, class_name: str, specialization: str) -> ScoringProfile:
    profile = session.scalar(
        select(ScoringProfile).where(
            ScoringProfile.class_name.ilike(class_name),
            ScoringProfile.specialization.ilike(specialization),
            ScoringProfile.active.is_(True),
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="No active scoring profile exists for this class and specialization.",
        )
    return profile


def _domain_profile(profile: ScoringProfile) -> DomainProfile:
    return DomainProfile(
        profile_id=profile.id,
        class_name=profile.class_name,
        specialization=profile.specialization,
        version=profile.version,
        active=profile.active,
        provisional=profile.provisional,
        weights={key: Decimal(str(value)) for key, value in profile.stat_weights.items()},
        adjustments={key: Decimal(str(value)) for key, value in profile.adjustments.items()},
        assumptions=profile.assumptions,
    )


def _character(request: CharacterRequest) -> Character:
    return Character(
        request.class_name, request.specialization, request.faction, request.level, request.race
    )


def _capabilities(session: Session, class_name: str) -> ClassCapabilities | None:
    row = session.scalar(
        select(ClassCapabilityProfile).where(
            ClassCapabilityProfile.class_name.ilike(class_name),
            ClassCapabilityProfile.ruleset_key == "wow_forever",
        )
    )
    if row is None:
        return None
    return ClassCapabilities(
        row.class_name,
        row.verification_status,
        tuple(row.armor_types) if row.armor_types is not None else None,
        tuple(row.weapon_types) if row.weapon_types is not None else None,
    )


def _item_model(item: Item) -> EquipmentItem:
    return EquipmentItem(
        item_id=item.id,
        name=item.name,
        slot=item.inventory_type,
        required_level=item.required_level,
        armor_type=item.armor_type,
        weapon_type=item.weapon_type,
        verification_status=item.verification_status,
        eligibility_status=item.eligibility_status,
        statistics_status=item.statistics_status,
        stats={stat.stat_type: Decimal(stat.value) for stat in item.stats},
        effects=tuple(effect.description or effect.effect_type for effect in item.effects),
        restrictions=tuple(
            Restriction(r.restriction_type, r.restriction_value, r.verification_status)
            for r in item.restrictions
        ),
        armor_value=Decimal(item.armor_value) if item.armor_value is not None else None,
        weapon_damage_min=Decimal(item.weapon_damage_min)
        if item.weapon_damage_min is not None
        else None,
        weapon_damage_max=Decimal(item.weapon_damage_max)
        if item.weapon_damage_max is not None
        else None,
        weapon_speed=Decimal(item.weapon_speed) if item.weapon_speed is not None else None,
    )


def _load_item(session: Session, item_id: int) -> Item:
    item = session.scalar(
        select(Item)
        .options(
            selectinload(Item.stats),
            selectinload(Item.effects),
            selectinload(Item.restrictions),
            selectinload(Item.acquisitions),
        )
        .where(Item.id == item_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found.")
    return item


def _score_read(item: Item, result) -> ScoreRead:
    return ScoreRead(
        item_id=item.id,
        item_name=item.name,
        status=result.status,
        score=float(result.score) if result.score is not None else None,
        eligibility=EligibilityRead(
            status=result.eligibility.status, reasons=list(result.eligibility.reasons)
        ),
        contributions=[
            {
                "stat_type": c.stat_type,
                "value": float(c.value),
                "weight": float(c.weight),
                "contribution": float(c.contribution),
            }
            for c in result.contributions
        ],
        missing_information=list(result.missing_information),
        unsupported_statistics=list(result.unsupported_statistics),
        unweighted_statistics=list(result.unweighted_statistics),
        provisional=result.provisional,
        profile_version=result.profile_version,
        calculation_version=result.calculation_version,
    )


@router.get("/scoring-profiles", response_model=list[ScoringProfileRead])
def list_scoring_profiles(
    session: SessionDep,
    class_name: str | None = Query(default=None),
    specialization: str | None = Query(default=None),
) -> list[ScoringProfile]:
    query = select(ScoringProfile).where(ScoringProfile.active.is_(True))
    if class_name:
        query = query.where(ScoringProfile.class_name.ilike(class_name))
    if specialization:
        query = query.where(ScoringProfile.specialization.ilike(specialization))
    return list(
        session.scalars(query.order_by(ScoringProfile.class_name, ScoringProfile.specialization))
    )


@router.get("/scoring-profiles/{profile_id}", response_model=ScoringProfileRead)
def get_scoring_profile(profile_id: int, session: SessionDep) -> ScoringProfile:
    profile = session.get(ScoringProfile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Scoring profile not found.")
    return profile


@router.post("/items/{item_id}/eligibility", response_model=EligibilityRead)
def check_item_eligibility(
    item_id: int, request: ItemCheckRequest, session: SessionDep
) -> EligibilityRead:
    item = _load_item(session, item_id)
    result = evaluate_eligibility(
        _item_model(item),
        _character(request),
        requested_slot=request.slot,
        capabilities=_capabilities(session, request.class_name),
    )
    return EligibilityRead(status=result.status, reasons=list(result.reasons))


@router.post("/items/{item_id}/score", response_model=ScoreRead)
def calculate_item_score(item_id: int, request: CharacterRequest, session: SessionDep) -> ScoreRead:
    item = _load_item(session, item_id)
    profile = _profile_row(session, request.class_name, request.specialization)
    result = score_item(
        _item_model(item),
        _domain_profile(profile),
        _character(request),
        capabilities=_capabilities(session, request.class_name),
    )
    return _score_read(item, result)


@router.post("/items/compare", response_model=ItemComparisonRead)
def compare_catalog_items(request: ItemCompareRequest, session: SessionDep) -> ItemComparisonRead:
    if canonical_slot(request.slot) is None:
        raise HTTPException(status_code=422, detail="Unsupported equipment slot.")
    if len(set(request.item_ids)) != len(request.item_ids):
        raise HTTPException(status_code=422, detail="Duplicate item IDs are not allowed.")
    rows = [_load_item(session, item_id) for item_id in request.item_ids]
    profile = _profile_row(session, request.class_name, request.specialization)
    try:
        ordered = compare_items(
            [_item_model(row) for row in rows],
            _domain_profile(profile),
            _character(request),
            slot=request.slot,
            capabilities=_capabilities(session, request.class_name),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    by_id = {row.id: row for row in rows}
    results = [_score_read(by_id[item.item_id], result) for item, result in ordered]
    ranked = all(result.score is not None for result in (pair[1] for pair in ordered))
    return ItemComparisonRead(
        slot=request.slot,
        items=results,
        ranked=ranked,
        explanation=(
            "Scores are item-level comparisons only; they do not optimize a complete equipment set."
        )
        if ranked
        else "Some item results are incomplete or ineligible and remain unranked.",
    )


@router.get("/planner/recommendations", response_model=GearPlanResponse)
def read_gear_plan(
    session: SessionDep,
    class_name: str = Query(min_length=1, max_length=30),
    specialization: str = Query(min_length=1, max_length=50),
    faction: Literal["Alliance", "Horde"] = Query(),
    level: int = Query(ge=1, le=60),
) -> GearPlanResponse:
    """Aggregate verified, scored item candidates for each planner slot."""
    profile_row = _profile_row(session, class_name, specialization)
    profile = _domain_profile(profile_row)
    character = Character(class_name, specialization, faction, level)
    capabilities = _capabilities(session, class_name)
    records = list(
        session.scalars(
            select(Item).where(Item.inventory_type.is_not(None)).options(*item_load_options())
        )
    )
    item_models = {item.id: _item_model(item) for item in records}
    records_by_id = {item.id: item for item in records}

    slots: list[PlannerSlot] = []
    for slot_id, label in PLANNER_SLOTS:
        family = _SLOT_FAMILY.get(slot_id, canonical_slot(label))
        matching = [item for item in records if canonical_slot(item.inventory_type) == family]
        comparisons = (
            compare_items(
                [item_models[item.id] for item in matching],
                profile,
                character,
                slot=label,
                capabilities=capabilities,
            )
            if matching
            else []
        )
        valid = [
            (item_model, result)
            for item_model, result in comparisons
            if result.status == "scored"
            and result.score is not None
            and result.eligibility.status == "eligible"
            and item_models[item_model.item_id].verification_status == "verified"
            and records_by_id[item_model.item_id].availability_status.casefold() == "available"
        ]
        explanations: list[str] = []
        if not profile.weights:
            explanations.append("Scoring profile is not configured: no weights are available.")
        elif profile.provisional:
            explanations.append(
                "Scoring profile is provisional; scores cannot establish recommendations."
            )
        if not matching:
            explanations.append("No catalog item records are available for this slot.")
        else:
            for item_model, result in comparisons:
                if result.status == "scored":
                    continue
                if item_models[item_model.item_id].verification_status != "verified":
                    explanations.append("Candidate item verification is incomplete.")
                catalog_row = records_by_id[item_model.item_id]
                if catalog_row.availability_status.casefold() == "unknown":
                    explanations.append("Item availability is unknown.")
                elif catalog_row.availability_status.casefold() != "available":
                    explanations.append("Item is not marked available.")
                explanations.extend(result.missing_information)
                if result.eligibility.status == "unknown":
                    explanations.extend(result.eligibility.reasons)
            if not valid and not explanations:
                explanations.append(
                    "No catalog candidate is eligible for this character and level."
                )

        def to_candidate(item_model, result, difference=None) -> PlannerCandidate:
            catalog_row = records_by_id[item_model.item_id]
            return PlannerCandidate(
                item=CatalogItemRead.model_validate(catalog_row),
                result=_score_read(catalog_row, result),
                score_difference=difference,
            )

        recommendation = None
        alternatives: list[PlannerCandidate] = []
        if valid:
            best_model, best_result = valid[0]
            recommendation = to_candidate(best_model, best_result)
            best_score = best_result.score
            alternatives = [
                to_candidate(
                    item_model,
                    result,
                    float(best_score - result.score),
                )
                for item_model, result in valid[1:5]
            ]
            explanations = [
                "Highest individual item score among verified, eligible candidates for this slot.",
                "This does not optimize the complete equipment set.",
            ]

        status = (
            "recommended"
            if recommendation is not None
            else "insufficient_data"
            if matching
            and (
                any(result.status != "scored" for _, result in comparisons)
                or not profile.weights
                or profile.provisional
                or any(
                    records_by_id[model.item_id].availability_status.casefold() == "unknown"
                    for model, _ in comparisons
                )
            )
            else "unavailable"
        )
        slots.append(
            PlannerSlot(
                slot=label,
                slot_family=family or slot_id,
                status=status,
                recommendation=recommendation,
                alternatives=alternatives,
                eligible_count=sum(
                    result.eligibility.status == "eligible" for _, result in comparisons
                ),
                incomplete_count=sum(
                    result.status != "scored"
                    or records_by_id[model.item_id].verification_status != "verified"
                    or records_by_id[model.item_id].availability_status.casefold() != "available"
                    for model, result in comparisons
                ),
                explanation=list(dict.fromkeys(explanations)),
            )
        )

    return GearPlanResponse(
        character=PlannerCharacter(
            class_name=class_name,
            specialization=specialization,
            faction=faction,
            level=level,
        ),
        profile_version=profile.version,
        profile_provisional=profile.provisional,
        profile_configured=bool(profile.weights),
        profile_assumptions=profile.assumptions,
        slots=slots,
    )
