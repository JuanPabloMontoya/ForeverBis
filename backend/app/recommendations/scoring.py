"""Deterministic, explainable item scoring, independent of persistence and HTTP."""

from decimal import Decimal

from backend.app.recommendations.domain import (
    Character,
    ClassCapabilities,
    EquipmentItem,
    ScoreResult,
    ScoringProfile,
    StatContribution,
    StatType,
)
from backend.app.recommendations.eligibility import canonical_slot, evaluate_eligibility

CALCULATION_VERSION = "weighted-item-score-v1"
_STAT_ALIASES = {
    "strength": "strength",
    "agility": "agility",
    "stamina": "stamina",
    "intellect": "intellect",
    "spirit": "spirit",
    "attack power": "attack_power",
    "attack_power": "attack_power",
    "spell power": "spell_power",
    "spell_power": "spell_power",
    "healing power": "healing_power",
    "healing_power": "healing_power",
    "critical strike": "critical_strike",
    "crit": "critical_strike",
    "critical_strike": "critical_strike",
    "hit": "hit",
    "hit rating": "hit",
    "haste": "haste",
    "defense": "defense",
    "dodge": "dodge",
    "parry": "parry",
    "block": "block",
    "armor": "armor",
    "weapon damage min": "weapon_damage_min",
    "weapon_damage_min": "weapon_damage_min",
    "weapon damage max": "weapon_damage_max",
    "weapon_damage_max": "weapon_damage_max",
    "weapon speed": "weapon_speed",
    "weapon_speed": "weapon_speed",
}


def _normalized_stats(item: EquipmentItem) -> dict[str, Decimal]:
    result: dict[str, Decimal] = {}
    for name, value in item.stats.items():
        key = _STAT_ALIASES.get(name.strip().casefold())
        key = key or name.strip().casefold()
        result[key] = result.get(key, Decimal(0)) + Decimal(value)
    for name in ("armor_value", "weapon_damage_min", "weapon_damage_max", "weapon_speed"):
        value = getattr(item, name)
        if value is not None:
            key = "armor" if name == "armor_value" else name
            result.setdefault(key, Decimal(value))
    return result


def score_item(
    item: EquipmentItem,
    profile: ScoringProfile,
    character: Character,
    *,
    capabilities: ClassCapabilities | None = None,
) -> ScoreResult:
    eligibility = evaluate_eligibility(item, character, capabilities=capabilities)
    if (profile.class_name.casefold(), profile.specialization.casefold()) != (
        character.class_name.casefold(),
        character.specialization.casefold(),
    ):
        return ScoreResult(
            "incomplete",
            None,
            eligibility,
            (),
            ("Scoring profile does not match character class and specialization.",),
            (),
            (),
            profile.provisional,
            profile.version,
        )
    if eligibility.status != "eligible":
        return ScoreResult(
            "ineligible" if eligibility.status == "ineligible" else "incomplete",
            None,
            eligibility,
            (),
            eligibility.reasons,
            (),
            (),
            profile.provisional,
            profile.version,
        )

    missing: list[str] = []
    unsupported: list[str] = []
    unweighted: list[str] = []
    if item.statistics_status != "verified":
        missing.append(
            "Statistics completeness is not verified; absent values cannot be treated as zero."
        )
    normalized = _normalized_stats(item)
    contributions: list[StatContribution] = []
    score = Decimal(0)
    for raw_name, value in sorted(normalized.items()):
        if raw_name not in {stat.value for stat in StatType}:
            unsupported.append(raw_name)
            continue
        if raw_name not in profile.weights:
            unweighted.append(raw_name)
            continue
        weight = Decimal(profile.weights[raw_name])
        contribution = value * weight
        score += contribution
        contributions.append(StatContribution(raw_name, value, weight, contribution))
    if item.effects:
        missing.append("Item effects are present but no validated effect evaluator is configured.")
    if unsupported:
        missing.append("One or more statistics are unsupported by this scoring version.")
    if unweighted:
        missing.append("One or more present statistics have no profile weight.")
    if not profile.weights:
        missing.append("No statistic weights are configured for this profile.")
    if missing:
        return ScoreResult(
            "incomplete",
            None,
            eligibility,
            tuple(contributions),
            tuple(missing),
            tuple(unsupported),
            tuple(unweighted),
            profile.provisional,
            profile.version,
        )
    status = "provisional" if profile.provisional else "scored"
    return ScoreResult(
        status,
        score,
        eligibility,
        tuple(contributions),
        (),
        (),
        (),
        profile.provisional,
        profile.version,
    )


def compare_items(
    items: list[EquipmentItem],
    profile: ScoringProfile,
    character: Character,
    *,
    slot: str,
    capabilities: ClassCapabilities | None = None,
) -> list[tuple[EquipmentItem, ScoreResult]]:
    requested = canonical_slot(slot)
    if requested is None or not items:
        raise ValueError("A supported slot and at least one item are required.")
    if any(canonical_slot(item.slot) != requested for item in items):
        raise ValueError("Items can only be compared within the same equipment slot.")
    results = [
        (item, score_item(item, profile, character, capabilities=capabilities)) for item in items
    ]
    # Numeric scores sort first; incomplete/unknown scores stay explicitly unranked.
    return sorted(
        results,
        key=lambda pair: (pair[1].score is None, -(pair[1].score or Decimal(0)), pair[0].item_id),
    )
