# Catalog data quality report

## Bounded live validation

Observed on 7 November 2026 (America/Bogota), using the documented TheWoWDB Forever item list and detail endpoints. The import limit was three; no full dataset was requested.

| Measure | Result |
|---|---:|
| Retrieved | 3 |
| Validated | 3 |
| Failed validation | 0 |
| First run persisted | 3 |
| Second run created / updated | 0 / 3 |
| Duplicate source/build/item rows after rerun | 0 |
| Wowhead Forever links from audited allowlist | 3 of 3 |
| Quality issues recorded | 12 (4 per item) |

The three provider item IDs were 25 (Worn Shortsword), 35 (Bent Staff), and 36 (Worn Mace). All report build `wow_classic_beta-1.60.1.70532`. Their records remain `needs_review`; their `required_level` is null.

## Findings

1. **Required level conflict:** each list record reported `required_level = 1`; the corresponding detail record reported null. Neither representation is selected as authoritative. Both observations are retained in a field-level issue, and the normalized value remains unknown.
2. **Empty arrays:** each sampled detail response had empty stats, effects, and class-restriction arrays. These produce explicit `empty_array_semantics_unverified` issues. They do not establish that the item has no stats, effects, or restrictions.
3. **Other restrictions and acquisition:** the sample does not verify faction restrictions, armor/weapon restrictions beyond explicit fields, or acquisition sources. No values are inferred. Auction/faction market prices are not modeled as restrictions.
4. **Icons:** provider icon URLs are retained and rendered by URL; the implementation does not download or proxy image files. Asset-specific redistribution terms were not independently established.
5. **Wowhead:** the three URLs use the Forever namespace and matched the three IDs, names, and item levels in the Phase 1 audit and current provider sample. No broader ID equivalence is inferred. All other IDs or mismatches produce null links.

## Limits of this report

This is a three-record integration sample, not a representativeness or completeness claim. It does not validate the entire provider dataset, all item types, all builds, icon licensing, acquisition coverage, or character eligibility. The catalog is useful for testing the provider adapter and UI, but the observed fields are insufficient to make BIS or equipment recommendations. The full dataset was neither requested nor stored.

## Phase 3.1 bounded coverage check

On 7 November 2026 (America/Bogota), a read-only dry-run requested 10 summaries from the documented Forever item list and fetched their details. It retrieved 10, validated 8, and failed 2 (source IDs 41 and 42 returned HTTP 404). It persisted 0. The 8 valid records all had item types Armor or Weapon and covered only Main Hand, Two-Hand, Shirt, Legs and Feet. Shirt is not one of the planner's 17 slots. All eight detail responses had `stats=[]`, `effects=[]`, and `classes=[]`; all eight had null `required_level`, while their list summaries reported 0 or 1. The report recorded 32 quality issues (four per valid row). No empty field was changed into a zero, unrestricted flag or verified value.

A second dry-run requesting 100 items ended with a socket read timeout and no complete report. The timeout escaped the adapter's current retry/error conversion, so do not count this as 100 retrieved/validated records. No records from either Phase 3.1 dry-run were written. A later direct detail inspection of the same eight IDs confirmed their equipment type/slot and that sampled weapon objects expose `damage_min`, `damage_max`, `dps` and `speed` keys; values were not independently checked in game.

The documented tooltip route returned an HTML tooltip plus plain `fields` for ID 25, but its stats array was empty. The documented example tooltip ID 12640 returned HTTP 404 in the current Forever API. A documented generic cross-kind search query `q=worn` returned zero grouped hits; this is not evidence that the items are absent from the item list. The list route's documented `q` parameter remains a name filter only.

The current PostgreSQL data was queried read-only after the experiment: still 3 items, all `needs_review`; no new item, version or source records were added. All 3 persisted rows retain explicit Wowhead URLs from the Phase 3 audit. This review re-opened their destinations: Forever pages for IDs 25 and 35 showed the matching names and item level 2; ID 36 returned a robot-verification screen, so its prior mapping remains but could not be independently rechecked today. Among the 8 valid dry-run details, only IDs 25, 35 and 36 match the existing explicit allowlist; IDs 37, 38, 39, 40 and 43 remain unmapped. The 2 detail-404 IDs are not verified records.

See [catalog coverage](CATALOG_COVERAGE_AUDIT.md), [statistics](ITEM_STATISTICS_AUDIT.md), [acquisition sources](ACQUISITION_SOURCES_AUDIT.md), [provider comparison](PROVIDER_COMPARISON.md), and [leveling matrix](LEVELING_COVERAGE_MATRIX.md) for source-specific methods and limitations.

## Prompt 3 recovery and controlled write (8 November 2026)

The current PostgreSQL state was checked before this work: migration `20261108_0004`, 3 items (provider IDs 25, 35, 36), 27 scoring profiles, and 9 capability profiles. The existing three catalog rows were not updated or promoted. Additive migration `20261108_0005` was then applied; Alembic reports this as the head and `alembic check` reports no model/schema drift.

### Import totals

Seven bounded name searches were executed through the CLI, with a maximum of 3 summaries per query. A pagination-limit defect was found during the first four queries: the importer stopped after 2 of 3 summaries. The defect was fixed; each query was then re-run as a new snapshot. Existing rows were skipped by source/build/item identity and the remaining records were imported without duplicates.

| Measure | Actual result |
|---|---:|
| Item summaries processed in persisted snapshots | 29 |
| New items imported | 15 |
| Updated items | 0 |
| Skipped as already present | 8 |
| Detail failures (HTTP 404) | 6 |
| Imported items marked `needs_review` | 15 |
| Total catalog items after import | 18 |
| Total item data snapshots | 29 |

The snapshots are IDs 1–11. The first four are preserved as historical runs with two fetched records each; the corrected reruns are snapshots 5–11. Every row has an outcome record. Failures did not roll back successful rows. No raw provider JSON was written into reports; raw summary/detail payloads for all 15 imported records are held in PostgreSQL and their immutable `item_data_snapshots`.

### Current coverage and uncertainty

All 18 records are `needs_review`; zero are verified. The 15 new rows have raw payload and capture provenance. The 3 original rows retain their original identifying values, required-level nulls, statuses, and no raw-payload backfill. No rows contain normalized `ItemStat`, effects, restrictions, or acquisition relationships; empty arrays remain unverified, not proof of absence. Separately, the provider supplied weapon minimum/maximum damage and speed values for 9 of the 15 new records. These values are preserved as provider-reported, not manually verified; numeric armor was not supplied in this sample.

| Gear Planner slot family | Rows | Notes |
|---|---:|---|
| Main Hand (including provider Two-Hand and One-Hand) | 9 | Weapons only; no normalized stats in the sample |
| Back | 2 | Required level unknown |
| Chest | 1 | Required level unknown |
| Feet | 3 | Required level unknown |
| Ranged | 3 | Two required levels unknown; one level 3 |
| Head, Neck, Shoulders, Wrist, Hands, Waist, Legs, Ring, Trinket, Off Hand | 0 | No sample coverage |

Required-level distribution: 12 unknown; 3 at level 3; 1 at level 4; 1 at level 11; 1 at level 20; 1 at level 33. By bands, 1–10 has 3 known values, 11–20 has 2, 21–30 has 0, 31–40 has 1, and 41–50/51–60 have 0. These counts are descriptive, not verified eligibility. The search results also included six item-detail 404s.

Acquisition-source coverage is zero. The documented item detail records used here supplied no item-to-NPC, quest, vendor, profession, or instance relationship that could be persisted with evidence. No acquisition source was inferred. Existing individually mapped Wowhead Forever URLs remain on the three original rows only; none of the 15 new records received an automatically generated Wowhead URL.

The live catalog summary reports 18 items, all `needs_review`. The live planner endpoint returned all 17 slots and zero recommendations. This is expected: every record is unverified, and the 27 active class/spec profiles still have empty provisional weights. No synthetic production item, scoring profile, or recommendation was added.
