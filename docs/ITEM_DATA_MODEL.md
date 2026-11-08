# Item Data Model (Prompt 1)

The SQLAlchemy catalog remains source and snapshot aware. Migration `20261108_0004` is additive: it does not change or promote existing items.

## Catalog extensions

`ItemStat` remains the normalized, extensible statistic relation. Supported scoring keys are `strength`, `agility`, `stamina`, `intellect`, `spirit`, `attack_power`, `spell_power`, `healing_power`, `critical_strike`, `hit`, `haste`, `defense`, `dodge`, `parry`, `block`, `armor`, `weapon_damage_min`, `weapon_damage_max`, and `weapon_speed`.

Nullable `Item.armor_value`, `weapon_damage_min`, `weapon_damage_max`, and `weapon_speed` support provider fields that arrive outside `stats[]`. `Item.last_validated_at` is nullable. `statistics_status` and `eligibility_status` independently express completeness; both default to `unknown`. `Item.verification_status` remains intact. Unknown numbers stay NULL; no migration infers stats, restrictions, or item eligibility.

Restrictions continue to use `ItemRestriction` and must be individually marked verified before affecting eligibility.

`AcquisitionSource` and `ItemAcquisition` provide nullable/provenance-aware foundations for drops, quests, vendors, professions, and other future source types. The migration seeds no acquisition records because the current provider audit did not establish verified item-source relationships. Unverified requirements remain unknown.

## Profiles and capabilities

`ScoringProfile` is unique by class, specialization, and version. JSON maps store editable canonical statistic weights and reserved extension adjustments; profiles also retain role, active/provisional flags, assumptions, and version. The schema deliberately seeds no weights.

`ClassCapabilityProfile` has one Forever ruleset row per class. Armor/weapon lists are NULL and verification is `unknown` initially. NULL means unverified, not “all proficiencies.”

## Snapshot and internal patch identity

`ForeverPatch` is an internal identity registry, separate from a provider/client build. `GameVersion.patch_id` is nullable and references it. Existing snapshots remain unassigned; no patch is inferred from an item creation date or external patch label. A full patch publishing/history workflow is out of scope.

Catalog identity still uses the existing provider ID and game-version uniqueness. This migration does not add a second entity identity or rewrite historical catalog rows.

## Existing records

The three imported production rows remain at their prior review status. New completeness columns default to `unknown`, preventing them from being treated as eligible or scored as recommendations.
