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
