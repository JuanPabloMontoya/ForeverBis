"""Normalize TheWoWDB item responses without filling unknown fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse

from backend.app.ingestion.providers.schemas import ItemListRecord, ItemResponse


@dataclass(frozen=True)
class NormalizedStat:
    stat_type: str
    value: Decimal


@dataclass(frozen=True)
class NormalizedEffect:
    effect_type: str
    description: str | None
    spell_id: int | None


@dataclass(frozen=True)
class NormalizedRestriction:
    restriction_type: str
    restriction_value: str


@dataclass(frozen=True)
class FieldIssue:
    field_name: str
    issue_code: str
    message: str
    observed_values: dict[str, Any] | list[Any] | None = None


@dataclass(frozen=True)
class NormalizedItem:
    source_item_id: int
    name: str
    quality: str | None
    item_level: int | None
    required_level: int | None
    inventory_type: str | None
    armor_type: str | None
    weapon_type: str | None
    icon_url: str | None
    source_item_url: str | None
    wowhead_url: str | None
    build: str | None
    stats: list[NormalizedStat] = field(default_factory=list)
    effects: list[NormalizedEffect] = field(default_factory=list)
    restrictions: list[NormalizedRestriction] = field(default_factory=list)
    issues: list[FieldIssue] = field(default_factory=list)


class ItemNormalizationError(ValueError):
    """A provider record cannot safely be normalized as a Forever item."""


_VERIFIED_WOWHEAD: dict[int, tuple[str, int, str]] = {
    25: ("Worn Shortsword", 2, "https://www.wowhead.com/forever/item=25/worn-shortsword"),
    35: ("Bent Staff", 2, "https://www.wowhead.com/forever/item=35/bent-staff"),
    36: ("Worn Mace", 2, "https://www.wowhead.com/forever/item=36/worn-mace"),
}


def verified_wowhead_url(detail: ItemResponse) -> str | None:
    """Return only an audited Forever URL whose identity fields still match."""
    expected = _VERIFIED_WOWHEAD.get(detail.id)
    if not expected or detail.version != "forever":
        return None
    expected_name, expected_level, url = expected
    if detail.name != expected_name or detail.item_level != expected_level:
        return None
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "www.wowhead.com":
        return None
    return url


def _provider_item_url(detail: ItemResponse) -> str | None:
    candidate = detail.attribution.url if detail.attribution else None
    if candidate is None and detail.links:
        candidate = detail.links.html
    if not candidate:
        return None
    parsed = urlparse(candidate)
    if parsed.scheme == "https" and parsed.netloc == "thewowdb.com":
        return candidate
    return None


def _icon_url(value: str | None) -> str | None:
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return value


def _armor_type(armor: dict[str, Any] | None) -> str | None:
    if not armor:
        return None
    for key in ("type", "armor_type", "name"):
        candidate = armor.get(key)
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()
    return None


def _numeric_value(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
    except InvalidOperation:
        return None
    return parsed if parsed.is_finite() else None


def _normalize_stats(entries: list[Any] | None, issues: list[FieldIssue]) -> list[NormalizedStat]:
    if entries is None or not entries:
        issues.append(
            FieldIssue(
                "stats",
                "empty_array_semantics_unverified",
                "No stat entries were reported; this does not prove the item has no stats.",
                entries,
            )
        )
        return []
    output: list[NormalizedStat] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(
                FieldIssue(
                    "stats", "unsupported_entry_shape", f"Stat entry {index} is not an object."
                )
            )
            continue
        stat_type = next(
            (
                entry.get(key)
                for key in ("stat_type", "type", "name", "stat")
                if isinstance(entry.get(key), str)
            ),
            None,
        )
        raw_value = next(
            (entry[key] for key in ("value", "amount") if key in entry),
            None,
        )
        numeric = _numeric_value(raw_value)
        if not stat_type or numeric is None:
            issues.append(
                FieldIssue(
                    "stats",
                    "unsupported_entry_shape",
                    f"Stat entry {index} lacks a recognized type/value.",
                )
            )
            continue
        output.append(NormalizedStat(stat_type=stat_type.strip(), value=numeric))
    return output


def _plain_text(value: str | None) -> str | None:
    if value is None:
        return None
    return " ".join(re.sub(r"<[^>]*>", " ", value).split())[:2000] or None


def _normalize_effects(
    entries: list[Any] | None, issues: list[FieldIssue]
) -> list[NormalizedEffect]:
    if entries is None or not entries:
        issues.append(
            FieldIssue(
                "effects",
                "empty_array_semantics_unverified",
                "No effect entries were reported; this does not prove the item has no effects.",
                entries,
            )
        )
        return []
    output: list[NormalizedEffect] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(
                FieldIssue(
                    "effects", "unsupported_entry_shape", f"Effect entry {index} is not an object."
                )
            )
            continue
        effect_type = next(
            (entry.get(key) for key in ("effect_type", "type") if isinstance(entry.get(key), str)),
            None,
        )
        description = next(
            (entry.get(key) for key in ("description", "text") if isinstance(entry.get(key), str)),
            None,
        )
        spell_id = entry.get("spell_id")
        if isinstance(spell_id, bool) or not isinstance(spell_id, int) or spell_id <= 0:
            spell_id = None
        if not effect_type:
            issues.append(
                FieldIssue(
                    "effects", "unsupported_entry_shape", f"Effect entry {index} has no type."
                )
            )
            continue
        output.append(NormalizedEffect(effect_type.strip(), _plain_text(description), spell_id))
    return output


def _normalize_restrictions(
    classes: list[Any] | None, issues: list[FieldIssue]
) -> list[NormalizedRestriction]:
    if classes is None or not classes:
        issues.append(
            FieldIssue(
                "classes",
                "empty_array_semantics_unverified",
                "No class restrictions were reported; unrestricted use is not established.",
                classes,
            )
        )
        return []
    output: list[NormalizedRestriction] = []
    for index, entry in enumerate(classes):
        value = entry if isinstance(entry, str) else None
        if isinstance(entry, dict):
            value = next(
                (entry.get(key) for key in ("name", "class") if isinstance(entry.get(key), str)),
                None,
            )
        if not value or not value.strip():
            issues.append(
                FieldIssue(
                    "classes",
                    "unsupported_entry_shape",
                    f"Class entry {index} has no recognized name.",
                )
            )
            continue
        output.append(NormalizedRestriction("class", value.strip()))
    return output


def normalize_item(summary: ItemListRecord, detail: ItemResponse) -> NormalizedItem:
    if summary.id != detail.id:
        raise ItemNormalizationError("List and detail item IDs do not match")
    if summary.version != "forever" or detail.version != "forever":
        raise ItemNormalizationError("Only documented Forever item records can be imported")
    if summary.name != detail.name:
        raise ItemNormalizationError("List and detail item names do not match")

    issues: list[FieldIssue] = []
    required_level = detail.required_level
    if summary.required_level != detail.required_level:
        required_level = None
        issues.append(
            FieldIssue(
                "required_level",
                "list_detail_conflict",
                "List and detail disagree; required level stays unknown pending review.",
                {"list": summary.required_level, "detail": detail.required_level},
            )
        )

    stats = _normalize_stats(detail.stats, issues)
    effects = _normalize_effects(detail.effects, issues)
    restrictions = _normalize_restrictions(detail.classes, issues)
    weapon_type = (
        detail.item_subtype
        if detail.item_type and detail.item_type.casefold() == "weapon"
        else None
    )

    return NormalizedItem(
        source_item_id=detail.id,
        name=detail.name.strip(),
        quality=detail.quality.casefold() if detail.quality else None,
        item_level=detail.item_level,
        required_level=required_level,
        inventory_type=detail.slot,
        armor_type=_armor_type(detail.armor),
        weapon_type=weapon_type,
        icon_url=_icon_url(detail.icon_url),
        source_item_url=_provider_item_url(detail),
        wowhead_url=verified_wowhead_url(detail),
        build=detail.build,
        stats=stats,
        effects=effects,
        restrictions=restrictions,
        issues=issues,
    )
