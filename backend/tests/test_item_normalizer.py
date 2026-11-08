"""Normalization and data quality behavior for provider records."""

import pytest
from pydantic import ValidationError

from backend.app.ingestion.normalizers.items import ItemNormalizationError, normalize_item
from backend.app.ingestion.providers.schemas import ItemListRecord, ItemResponse


def make_summary(**updates):
    data = {
        "id": 25,
        "kind": "item",
        "version": "forever",
        "name": "Worn Shortsword",
        "quality": "common",
        "item_level": 2,
        "required_level": 1,
    }
    data.update(updates)
    return ItemListRecord.model_validate(data)


def make_detail(**updates):
    data = {
        "id": 25,
        "kind": "item",
        "version": "forever",
        "name": "Worn Shortsword",
        "quality": "common",
        "item_level": 2,
        "required_level": None,
        "item_type": "Weapon",
        "item_subtype": "One-Handed Sword",
        "slot": "Main Hand",
        "weapon": {"damage_min": 1, "damage_max": 3},
        "armor": None,
        "stats": [],
        "effects": [],
        "classes": [],
        "icon_url": "https://render.worldofwarcraft.com/us/icons/56/inv_sword_04.jpg",
        "build": "mock-build",
        "links": {"html": "https://thewowdb.com/wow-forever/item/worn-shortsword-25/"},
        "attribution": {
            "required": True,
            "text": "Data from TheWoWDB (thewowdb.com)",
            "url": "https://thewowdb.com/wow-forever/item/worn-shortsword-25/",
        },
    }
    data.update(updates)
    return ItemResponse.model_validate(data)


def test_required_level_conflict_stays_unknown_and_is_reported():
    item = normalize_item(make_summary(), make_detail())
    assert item.required_level is None
    issue = next(issue for issue in item.issues if issue.field_name == "required_level")
    assert issue.issue_code == "list_detail_conflict"
    assert issue.observed_values == {"list": 1, "detail": None}
    assert item.inventory_type == "Main Hand"
    assert item.weapon_type == "One-Handed Sword"
    assert item.wowhead_url == "https://www.wowhead.com/forever/item=25/worn-shortsword"


def test_empty_stats_effects_and_classes_are_unknown_not_none():
    item = normalize_item(make_summary(), make_detail())
    issue_fields = {issue.field_name for issue in item.issues}
    assert {"stats", "effects", "classes", "required_level"} <= issue_fields
    assert item.stats == []
    assert item.restrictions == []


def test_nonempty_supported_values_normalize_without_fabricating_fields():
    detail = make_detail(
        required_level=1,
        stats=[{"type": "Strength", "value": 4}],
        effects=[{"type": "equip", "description": "Equip: <b>Test effect</b>", "spell_id": 12}],
        classes=["Warrior"],
    )
    item = normalize_item(make_summary(), detail)
    assert item.required_level == 1
    assert [(stat.stat_type, stat.value) for stat in item.stats] == [("Strength", 4)]
    assert item.effects[0].description == "Equip: Test effect"
    assert item.restrictions[0].restriction_value == "Warrior"
    assert item.issues == []


def test_unrecognized_nested_fields_are_flagged_and_not_guessed():
    item = normalize_item(
        make_summary(required_level=1),
        make_detail(
            required_level=1,
            stats=[{"mystery": 5}],
            effects=[{"spell_id": 123}],
            classes=[{"id": 9}],
        ),
    )
    assert not item.stats
    assert not item.effects
    assert not item.restrictions
    assert {issue.issue_code for issue in item.issues} == {"unsupported_entry_shape"}


def test_verified_wowhead_mapping_requires_name_and_item_level_match():
    assert normalize_item(make_summary(), make_detail()).wowhead_url is not None
    mismatch = make_detail(name="A different item")
    with pytest.raises(ItemNormalizationError, match="names do not match"):
        normalize_item(make_summary(), mismatch)
    no_mapping = make_detail(id=999, name="Not mapped")
    no_mapping_summary = make_summary(id=999, name="Not mapped", required_level=None)
    assert normalize_item(no_mapping_summary, no_mapping).wowhead_url is None


def test_invalid_provider_item_version_is_rejected():
    with pytest.raises(ValidationError, match="forever"):
        make_detail(version="retail")
