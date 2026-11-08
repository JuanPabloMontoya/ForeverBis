# Leveling Coverage Matrix

**Audit date:** 7 November 2026. No BIS or gear scoring was performed.

## Current persisted catalog

The PostgreSQL snapshot was queried read-only. It contains 3 items, all `needs_review`, from TheWoWDB build `wow_classic_beta-1.60.1.70532`:

| Source ID | Name | Reported slot | Quality | Item level | Required character level | Verification |
|---:|---|---|---:|---:|---|---|
| 25 | Worn Shortsword | Main Hand | common | 2 | Unknown (`NULL`) | needs_review |
| 35 | Bent Staff | Two-Hand | common | 2 | Unknown (`NULL`) | needs_review |
| 36 | Worn Mace | Main Hand | common | 2 | Unknown (`NULL`) | needs_review |

They cannot establish eligibility at any character level: the list/detail required-level conflict remains unresolved, all three have unverified empty stat/effect/class arrays, and none is verified for class/faction availability. Thus **verified progression-item coverage is zero in every level band**.

## Bounded first-page sample

The successful 10-summary dry-run retrieved 8 valid gear details and 2 detail 404s. It covered Main Hand, Two-Hand, Shirt, Legs and Feet only. Shirt is not a slot in the 17-slot planner. The details had item levels 1–2; all detail required levels were null. The sample had no populated stats, effects or class restrictions. It is an intentionally narrow first-page sample, so absence of higher-level gear or other slots here does not prove absence from the provider's full data.

| Level range | Persisted verified items | Evidence from first 10 list results | Coverage assessment |
|---|---:|---|---|
| 1–10 | 0 | IDs 25, 35, 36, 37, 38, 39, 40 and 43 had item levels 1–2, but required levels were null; all need review. | Some low-level item identities are visible; no verified character-level eligibility or usable stats. |
| 11–20 | 0 | No verified evidence in the bounded sample. | Not established. |
| 21–30 | 0 | No verified evidence in the bounded sample. | Not established. |
| 31–40 | 0 | No verified evidence in the bounded sample. | Not established. |
| 41–50 | 0 | No verified evidence in the bounded sample. | Not established. |
| 51–60 | 0 | No verified evidence in the bounded sample. | Not established. |

The range table uses required character level as the relevant progression field. Item level is not a substitute. Zero means “no currently verified persisted row,” not “the game has no item for this level.”

## Slot coverage

Among persisted records, only Main Hand (2 rows) and a provider `Two-Hand` row appear; all three are unverified. The first 10 live list results add one Legs, two Feet and one Shirt row in the detail sample, plus additional weapons. No valid detail in that sample covered Head, Neck, Shoulders, Back, Chest, Wrist, Hands, Waist, Rings, Trinkets, Off Hand as a distinct equip type or Ranged. This does not establish provider-wide absence.

| Planner slot | Verified current records |
|---|---:|
| Head, Neck, Shoulders, Back, Chest, Wrist, Hands, Waist | 0 each |
| Legs, Feet | 0 each |
| Ring 1, Ring 2, Trinket 1, Trinket 2 | 0 each |
| Main Hand, Off Hand, Ranged | 0 each |

The `Two-Hand` inventory type should be modeled as a compatibility rule only after equip semantics are verified; do not silently count it as independent off-hand coverage.

## Feasibility for all nine classes

Current evidence is not sufficient for a level-by-level planner for any class, and far from enough for nine classes × specializations × factions × 60 levels × equipment slots. The first-page response is biased, filters by slot/quality/level are not documented, required level conflicts with detail data, stats/restrictions are empty or unverified, and acquisition relations are not present in TheWoWDB item contract. There is no reliable way yet to determine which candidate is usable or obtainable for a selected character.

Before BIS implementation, obtain authorized, build-versioned coverage for wearable item identities and full stats; verified required level and class/faction/race/proficiency restrictions; item-to-source relationships and prerequisites; a field-level review process; and a documented recommendation method by class/spec/level. See [statistics audit](ITEM_STATISTICS_AUDIT.md), [acquisition audit](ACQUISITION_SOURCES_AUDIT.md) and [provider comparison](PROVIDER_COMPARISON.md).

## Phase 3.2 cross-provider evidence

Wowhead's public Forever Item Finder offers filters/ranges `1–19`, `20–29`, `30–39`, `40–49`, `50–59`, `60`, plus source, slot and class/spec controls. These are visible UI filters, not a verified complete item inventory. Individual public pages demonstrate that some records in several ranges have data:

- 1–10: the Forever page for [Mace, ID 852](https://www.wowhead.com/forever/item=852/mace) shows required level 9.
- 11–20: no specific item page was verified in this audit. The Finder's 1–19 range does not give a count for 11–20.
- 21–30: [Refractory Scaleguards, ID 273048](https://www.wowhead.com/forever/item=273048/refractory-scaleguards) shows required level 28 and a named drop source.
- 31–40: [Mender's Mail Boots pattern, ID 252899](https://www.wowhead.com/forever/item=252899/pattern-menders-mail-boots) shows the crafted item requirement at level 40, along with a recipe/materials path and drop information for the pattern.
- 41–50: [Mender's Mail Shoulders, ID 252569](https://www.wowhead.com/forever/item=252569/menders-mail-shoulders) shows required level 42; [Mender's Mail Gauntlets, ID 252587](https://www.wowhead.com/forever/item=252587/menders-mail-gauntlets) shows level 50.
- 51–60: [Premier Mail Helm, ID 272486](https://www.wowhead.com/forever/item=272486/premier-mail-helm) shows level 55, stats, armor and a Shaman class restriction.

These examples prove that pages with level and gear data can be viewed in multiple ranges. They do not establish complete slot coverage, correctness against the live server, usable source records for all items, or permission to copy them into a local dataset. Wowhead's public terms restrict automated downloading by crawlers/agents absent permission; these rows are manual references only.

TheWoWDB's 8 previously validated details are all item level 1–2 and have unknown required level; none supplies verified range eligibility. In Phase 3.2, list/detail requests for 30 items and a smaller refresh repeatedly timed out before a complete report. Do not treat these failures as an empty dataset or as 30 examined objects. PostgreSQL still has only the three unverified low-item-level records.

| Required-level band | Wowhead public page evidence | TheWoWDB persisted/validated evidence | What can be concluded |
|---|---|---|---|
| 1–10 | One visible Forever page example, required level 9. | 0 verified; first sample details item level 1–2 but required level unknown. | Existence is evidenced; usable catalog coverage is not. |
| 11–20 | Finder includes broad 1–19 range, but no item page was individually verified in that exact band. | 0 verified; no sample detail with confirmed required level. | Not established. |
| 21–30 | One visible page example, required level 28. | 0 verified; no sample detail with confirmed required level. | Existence is evidenced on Wowhead only; local reuse not authorized. |
| 31–40 | Visible crafted/drop example, required level 40. | 0 verified; no sample detail with confirmed required level. | An example exists, not a complete progression pool. |
| 41–50 | Visible examples at required levels 42 and 50. | 0 verified; no sample detail with confirmed required level. | Examples exist on Wowhead only; no count/completeness. |
| 51–60 | Visible example at required level 55. | 0 verified; no sample detail with confirmed required level. | Example exists; level 60 and broader availability not established. |

**Overall:** Wowhead pages indicate public item visibility across parts of the level range; TheWoWDB has an authorized structured API but this live session did not permit the requested 30-record validation. Neither source, in the access mode permitted by the evidence reviewed, supports a complete local progression catalog for nine classes and all 17 slots.
