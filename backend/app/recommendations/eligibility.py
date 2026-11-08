"""Pure equipment eligibility evaluation; unknown facts remain unknown."""

from backend.app.recommendations.domain import (
    Character,
    ClassCapabilities,
    EligibilityResult,
    EquipmentItem,
)


def _key(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("_", " ").replace("-", " ").split())


def canonical_slot(value: str | None) -> str | None:
    key = _key(value)
    aliases = {
        "head": "head",
        "neck": "neck",
        "shoulder": "shoulders",
        "shoulders": "shoulders",
        "back": "back",
        "chest": "chest",
        "robe": "chest",
        "wrist": "wrist",
        "hands": "hands",
        "hand": "hands",
        "waist": "waist",
        "legs": "legs",
        "feet": "feet",
        "finger": "ring",
        "ring": "ring",
        "ring 1": "ring",
        "ring 2": "ring",
        "trinket": "trinket",
        "trinket 1": "trinket",
        "trinket 2": "trinket",
        "main hand": "main_hand",
        "one hand": "main_hand",
        "two hand": "main_hand",
        "off hand": "off_hand",
        "held in off hand": "off_hand",
        "shield": "off_hand",
        "ranged": "ranged",
        "thrown": "ranged",
        "relic": "ranged",
    }
    return aliases.get(key)


def evaluate_eligibility(
    item: EquipmentItem,
    character: Character,
    *,
    requested_slot: str | None = None,
    capabilities: ClassCapabilities | None = None,
) -> EligibilityResult:
    reasons: list[str] = []
    unknown: list[str] = []
    if not 1 <= character.level <= 60:
        return EligibilityResult("ineligible", ("Character level must be between 1 and 60.",))
    if item.verification_status != "verified" or item.eligibility_status != "verified":
        unknown.append("Item eligibility is not verified.")
    if item.required_level is None:
        unknown.append("Required character level is unknown.")
    elif character.level < item.required_level:
        reasons.append(
            f"Requires level {item.required_level}; character is level {character.level}."
        )
    wanted = canonical_slot(requested_slot) if requested_slot else None
    actual = canonical_slot(item.slot)
    if wanted and not actual:
        unknown.append("Item equipment slot is unknown or unsupported.")
    elif wanted and actual != wanted:
        reasons.append(f"Item slot {actual} does not match requested slot {wanted}.")
    elif not actual:
        unknown.append("Item equipment slot is unknown or unsupported.")

    class_name, faction = _key(character.class_name), _key(character.faction)
    race = _key(character.race) if character.race is not None else None
    for restriction in item.restrictions:
        kind, value = _key(restriction.restriction_type), _key(restriction.restriction_value)
        if kind not in {"class", "specialization", "faction", "race"}:
            unknown.append(f"{kind.title()} restriction cannot be evaluated by this engine.")
            continue
        if restriction.verification_status != "verified":
            unknown.append(f"{kind.title()} restriction is unverified.")
            continue
        selected = {
            "class": class_name,
            "specialization": _key(character.specialization),
            "faction": faction,
            "race": race,
        }[kind]
        if selected is None:
            unknown.append(f"Character {kind} is required to evaluate this restriction.")
        elif selected != value:
            reasons.append(f"Restricted to {restriction.restriction_value}.")

    if item.armor_type:
        if (
            capabilities is None
            or capabilities.verification_status != "verified"
            or capabilities.armor_types is None
        ):
            unknown.append("Class armor proficiency is unknown.")
        elif _key(item.armor_type) not in {_key(v) for v in capabilities.armor_types}:
            reasons.append(
                f"{character.class_name} cannot equip {item.armor_type} armor (verified profile)."
            )
    if item.weapon_type:
        if (
            capabilities is None
            or capabilities.verification_status != "verified"
            or capabilities.weapon_types is None
        ):
            unknown.append("Class weapon proficiency is unknown.")
        elif _key(item.weapon_type) not in {_key(v) for v in capabilities.weapon_types}:
            reasons.append(
                f"{character.class_name} lacks verified proficiency for {item.weapon_type}."
            )

    if reasons:
        return EligibilityResult("ineligible", tuple(reasons + unknown))
    if unknown:
        return EligibilityResult("unknown", tuple(dict.fromkeys(unknown)))
    return EligibilityResult("eligible", ("All modeled eligibility requirements are verified.",))
