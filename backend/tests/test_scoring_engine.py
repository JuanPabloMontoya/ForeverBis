"""Pure unit tests use synthetic test-only equipment, never production catalog rows."""

from decimal import Decimal

import pytest

from backend.app.recommendations.domain import (
    Character,
    ClassCapabilities,
    EquipmentItem,
    Restriction,
    ScoringProfile,
    StatType,
)
from backend.app.recommendations.eligibility import evaluate_eligibility
from backend.app.recommendations.scoring import compare_items, score_item


def character(**changes) -> Character:
    data = {"class_name": "Warrior", "specialization": "Arms", "faction": "Alliance", "level": 20}
    data.update(changes)
    return Character(**data)


def sample_item(**changes) -> EquipmentItem:
    data = {
        "item_id": 900001,
        "name": "Synthetic test sword",
        "slot": "Main Hand",
        "required_level": 1,
        "verification_status": "verified",
        "eligibility_status": "verified",
        "statistics_status": "verified",
        "stats": {"strength": Decimal(3)},
    }
    data.update(changes)
    return EquipmentItem(**data)


def profile(weights=None, provisional=False) -> ScoringProfile:
    return ScoringProfile(
        None,
        "Warrior",
        "Arms",
        "test-v1",
        True,
        provisional,
        weights if weights is not None else {"strength": Decimal("2")},
    )


def test_all_supported_statistics_are_normalized_and_explained():
    stats = {stat.value: Decimal("1.5") for stat in StatType}
    result = score_item(
        sample_item(stats=stats), profile({key: Decimal("2") for key in stats}), character()
    )
    assert result.status == "scored"
    assert result.score == Decimal("57.0")
    assert {part.stat_type for part in result.contributions} == {stat.value for stat in StatType}
    assert all(part.contribution == Decimal("3.0") for part in result.contributions)


def test_supported_legacy_labels_and_explicit_armor_weapon_fields():
    item = sample_item(
        stats={"Strength": Decimal(2)}, armor_value=Decimal(4), weapon_speed=Decimal(3)
    )
    result = score_item(
        item,
        profile({"strength": Decimal(1), "armor": Decimal(2), "weapon_speed": Decimal(-1)}),
        character(),
    )
    assert result.score == Decimal(7)


def test_unknown_statistics_completeness_and_unweighted_stats_are_incomplete():
    result = score_item(sample_item(statistics_status="unknown"), profile(), character())
    assert result.status == "incomplete"
    assert result.score is None
    assert "cannot be treated as zero" in result.missing_information[0]
    unweighted = score_item(
        sample_item(stats={"strength": Decimal(1), "agility": Decimal(2)}), profile(), character()
    )
    assert unweighted.status == "incomplete"
    assert unweighted.unweighted_statistics == ("agility",)


def test_unknown_and_unsupported_stat_is_reported():
    result = score_item(sample_item(stats={"mystery stat": Decimal(1)}), profile(), character())
    assert result.status == "incomplete"
    assert result.unsupported_statistics == ("mystery stat",)


def test_provisional_profile_returns_explainable_provisional_result():
    result = score_item(sample_item(), profile(provisional=True), character())
    assert result.status == "provisional"
    assert result.score == Decimal(6)
    assert result.provisional is True


def test_empty_profile_weights_are_incomplete():
    result = score_item(sample_item(), profile({}), character())
    assert result.status == "incomplete"
    assert result.score is None


def test_level_and_slot_eligibility():
    item = sample_item(required_level=21)
    assert evaluate_eligibility(item, character()).status == "ineligible"
    assert (
        evaluate_eligibility(sample_item(), character(), requested_slot="Head").status
        == "ineligible"
    )
    assert (
        evaluate_eligibility(sample_item(), character(), requested_slot="Main Hand").status
        == "eligible"
    )
    assert evaluate_eligibility(sample_item(required_level=None), character()).status == "unknown"


def test_unverified_item_and_restrictions_remain_unknown():
    assert (
        evaluate_eligibility(sample_item(verification_status="needs_review"), character()).status
        == "unknown"
    )
    restricted = sample_item(restrictions=(Restriction("class", "Mage", "verified"),))
    assert evaluate_eligibility(restricted, character()).status == "ineligible"
    faction = sample_item(restrictions=(Restriction("faction", "Horde", "verified"),))
    assert evaluate_eligibility(faction, character()).status == "ineligible"
    unknown = sample_item(restrictions=(Restriction("class", "Mage", "needs_review"),))
    assert evaluate_eligibility(unknown, character()).status == "unknown"


def test_race_restriction_requires_character_race():
    item = sample_item(restrictions=(Restriction("race", "Human", "verified"),))
    assert evaluate_eligibility(item, character()).status == "unknown"
    assert evaluate_eligibility(item, character(race="Human")).status == "eligible"


def test_armor_and_weapon_proficiency_unknown_and_verified():
    mail = sample_item(armor_type="Mail")
    assert evaluate_eligibility(mail, character()).status == "unknown"
    cannot_wear = ClassCapabilities("Warrior", "verified", ("Plate",), ("Sword",))
    assert evaluate_eligibility(mail, character(), capabilities=cannot_wear).status == "ineligible"
    can_wear = ClassCapabilities("Warrior", "verified", ("Mail",), ("One-Handed Sword",))
    assert (
        evaluate_eligibility(
            sample_item(weapon_type="One-Handed Sword"), character(), capabilities=can_wear
        ).status
        == "eligible"
    )
    unknown = ClassCapabilities("Warrior", "unknown", None, None)
    assert evaluate_eligibility(mail, character(), capabilities=unknown).status == "unknown"


def test_deterministic_scoring_and_same_slot_comparison():
    weak, strong = (
        sample_item(item_id=10, stats={"strength": Decimal(1)}),
        sample_item(item_id=11, stats={"strength": Decimal(4)}),
    )
    first = score_item(strong, profile(), character())
    second = score_item(strong, profile(), character())
    assert first == second
    assert [
        item.item_id
        for item, _ in compare_items([weak, strong], profile(), character(), slot="main_hand")
    ] == [11, 10]


def test_invalid_slot_comparison_is_rejected():
    with pytest.raises(ValueError, match="same equipment slot"):
        compare_items(
            [sample_item(), sample_item(item_id=12, slot="Head")],
            profile(),
            character(),
            slot="main_hand",
        )
