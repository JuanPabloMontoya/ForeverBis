# Forever Item Statistics Audit

**Audit date:** 7 November 2026. TheWoWDB live detail/tooltip observations used build `wow_classic_beta-1.60.1.70532`.

## TheWoWDB observations

The documented item-detail response has `stats`, `effects`, `armor`, and `weapon` fields. The tooltip endpoint returns rendered HTML plus a `fields` object with corresponding item fields. In the successful 10-summary dry-run, 8 valid gear details were fetched. Every one had `stats=[]`, `effects=[]`, and `classes=[]`. The list showed `required_level` 0 or 1 for sampled IDs where detail reported null. No stats were inferred from the tooltip; for ID 25, tooltip plain fields also had an empty stats array. A schema field being present does not prove its contents are complete or that an empty array means none.

| Field | Provider field / endpoint | Coverage in this audit | Forever-specific verification |
|---|---|---|---|
| Strength | `stats[]`, item detail and tooltip fields | Container present; no populated stat entries in 8/8 gear details. | Not verified against in-game tooltip. |
| Agility | `stats[]`, item detail and tooltip fields | Same; provider schema does not enumerate a stable stat-type vocabulary. | Not verified. |
| Stamina | `stats[]`, item detail and tooltip fields | Same. | Not verified. |
| Intellect | `stats[]`, item detail and tooltip fields | Same. | Not verified. |
| Spirit | `stats[]`, item detail and tooltip fields | Same. | Not verified. |
| Attack power | `stats[]`, item detail and tooltip fields | No populated stat entries in sample; no type mapping established. | Not verified. |
| Spell power | `stats[]`, item detail and tooltip fields | No populated stat entries in sample; no type mapping established. | Not verified. |
| Critical strike | `stats[]`, item detail and tooltip fields | No populated stat entries; exact Forever stat key not documented. | Not verified. |
| Hit rating | `stats[]`, item detail and tooltip fields | No populated stat entries; exact Forever stat key not documented. | Not verified. |
| Defense | `stats[]`, armor object and tooltip fields | No populated stat entries in sample; armor keys were absent for sampled rows. | Not verified. |
| Armor value/type | `armor` object, item detail and tooltip fields | `armor` field exists; sampled details did not populate armor object keys, including sampled armor records. | Not verified. |
| Weapon damage | `weapon.damage_min`, `weapon.damage_max` | Keys appeared in sampled weapon objects. Values/completeness were not compared with in-game tooltips in this audit. | Not verified. |
| Weapon speed | `weapon.speed` (and provider also exposes `dps`) | Keys appeared in sampled weapon objects. Values/completeness were not compared with in-game tooltips. | Not verified. |
| Item effects / proc description | `effects[]`, tooltip fields and rendered HTML | Empty in all 8 sample details and in ID 25 tooltip fields. | Not verified; empty does not mean no proc. |

The list/detail `required_level` conflict is independently observed: list values included 0/1 while detail values were null. Keep required level unknown until reconciled with a dependable Forever-specific source. Never substitute `item_level` for character required level.

## Complementary field evidence

Eternadex states that its item statistics are calculated from WoW Forever beta client game data and that the in-game tooltip takes precedence if server-side changes differ. It also says some server-only items are added from in-game tooltip observations. Its item database exposes stats and its public item pages expose tooltips. This is meaningful candidate evidence, but it is the provider's own methodology statement, not an independent field-by-field verification or a public redistribution license. Its current database page reported build `1.60.1.70790` (dated 4 Nov 2026), which differs from TheWoWDB's observed build. Do not merge values across builds without reconciliation.

No publicly documented Eternadex item-data API or bulk reuse license was found. Its documented tooltip embed is permission to display its tooltip script/link on a site; it does not establish permission to extract, store or republish the underlying item dataset. Seek written terms before automated use.

Wowhead Forever pages can serve as an individual cross-check only where the exact Forever item is verified. This audit did not scrape Wowhead or reuse tooltip content. Three records already have explicit matching mappings; this does not establish that the other provider IDs have equivalent definitions.

## What is needed for a trustworthy stats layer

1. An authorized Forever-specific source that supplies per-item stat values, a stable stat vocabulary, provenance and build.
2. A controlled comparison of non-empty examples across all stat categories and weapon/armor fields against the live Forever tooltip.
3. Explicit handling for server-only/unrevealed items and changed values.
4. Source-specific rights for storing and displaying icons and tooltip/stat data.
5. Reconciliation rules for list/detail disagreements, with unresolved values staying unknown.

References: [TheWoWDB API](https://thewowdb.com/developers/), [Eternadex database methodology](https://eternadex.com/en/datenbank/), [Eternadex About](https://eternadex.com/en/ueber/), [Eternadex tooltip embed terms](https://eternadex.com/en/tooltips/).
