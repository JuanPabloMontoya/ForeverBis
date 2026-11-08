"""Framework-independent contracts used by eligibility and item scoring."""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum


class StatType(StrEnum):
    STRENGTH = "strength"
    AGILITY = "agility"
    STAMINA = "stamina"
    INTELLECT = "intellect"
    SPIRIT = "spirit"
    ATTACK_POWER = "attack_power"
    SPELL_POWER = "spell_power"
    HEALING_POWER = "healing_power"
    CRITICAL_STRIKE = "critical_strike"
    HIT = "hit"
    HASTE = "haste"
    DEFENSE = "defense"
    DODGE = "dodge"
    PARRY = "parry"
    BLOCK = "block"
    ARMOR = "armor"
    WEAPON_DAMAGE_MIN = "weapon_damage_min"
    WEAPON_DAMAGE_MAX = "weapon_damage_max"
    WEAPON_SPEED = "weapon_speed"


class EquipmentSlot(StrEnum):
    HEAD = "head"
    NECK = "neck"
    SHOULDERS = "shoulders"
    BACK = "back"
    CHEST = "chest"
    WRIST = "wrist"
    HANDS = "hands"
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    TRINKET_1 = "trinket_1"
    TRINKET_2 = "trinket_2"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    RANGED = "ranged"


@dataclass(frozen=True)
class Character:
    class_name: str
    specialization: str
    faction: str
    level: int
    race: str | None = None


@dataclass(frozen=True)
class Restriction:
    restriction_type: str
    restriction_value: str
    verification_status: str


@dataclass(frozen=True)
class EquipmentItem:
    item_id: int
    name: str
    slot: str | None
    required_level: int | None
    armor_type: str | None = None
    weapon_type: str | None = None
    verification_status: str = "unknown"
    eligibility_status: str = "unknown"
    statistics_status: str = "unknown"
    stats: dict[str, Decimal] = field(default_factory=dict)
    effects: tuple[str, ...] = ()
    restrictions: tuple[Restriction, ...] = ()
    armor_value: Decimal | None = None
    weapon_damage_min: Decimal | None = None
    weapon_damage_max: Decimal | None = None
    weapon_speed: Decimal | None = None


@dataclass(frozen=True)
class ClassCapabilities:
    class_name: str
    verification_status: str
    armor_types: tuple[str, ...] | None
    weapon_types: tuple[str, ...] | None


@dataclass(frozen=True)
class ScoringProfile:
    profile_id: int | None
    class_name: str
    specialization: str
    version: str
    active: bool
    provisional: bool
    weights: dict[str, Decimal]
    adjustments: dict[str, Decimal] = field(default_factory=dict)
    assumptions: str = ""


@dataclass(frozen=True)
class EligibilityResult:
    status: str
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class StatContribution:
    stat_type: str
    value: Decimal
    weight: Decimal
    contribution: Decimal


@dataclass(frozen=True)
class ScoreResult:
    status: str
    score: Decimal | None
    eligibility: EligibilityResult
    contributions: tuple[StatContribution, ...]
    missing_information: tuple[str, ...]
    unsupported_statistics: tuple[str, ...]
    unweighted_statistics: tuple[str, ...]
    provisional: bool
    profile_version: str
    calculation_version: str = "weighted-item-score-v1"
