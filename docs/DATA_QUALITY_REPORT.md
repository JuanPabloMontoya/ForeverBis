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
