# Scoring Engine (Prompt 1)

## Scope and formula

The recommendation package is pure Python and has no FastAPI, SQLAlchemy, network, or database dependencies in its calculation path. It implements an item-level score only:

```text
item_score = Σ(stat_value × profile_weight)
```

Values are decimal numbers. Each result includes the input value, applied weight, and contribution for each statistic, plus profile and calculation versions. Input statistics are canonicalized from known labels. Unsupported names, present but unweighted stats, incomplete stat coverage, unknown eligibility, and unevaluated effects prevent a numeric result or make it explicitly incomplete. They are never silently treated as zero.

If the item has no effects and its `statistics_status` is explicitly `verified`, an omitted statistic is considered absent from that verified stat record. An empty provider array alone is not such verification.

## Eligibility before scoring

`eligibility.py` runs first. It checks character level, supported equipment slot, overall item and eligibility verification, class/spec/faction/race restrictions, and armor/weapon proficiency. Outcomes are `eligible`, `ineligible`, or `unknown`. Unknown eligibility never produces a score. Restrictions and class capability lists must carry `verified` status before being used as positive evidence.

The 17 paper-doll slots map to equipment families for item comparisons: Head, Neck, Shoulders, Back, Chest, Wrist, Hands, Waist, Legs, Feet, Ring 1/2 (Finger family), Trinket 1/2 (Trinket family), Main Hand, Off Hand, and Ranged. Items from different families cannot be compared. A two-hand item maps to the main-hand family; this is only a slot-family check, not a complete dual-wield or equipment-set solver.

## Weights and provisional status

`ScoringProfile` persists class, specialization, optional role, version, active/provisional flags, assumptions, statistic weights, and extension adjustments. GET endpoints expose profiles, while profile editing is intentionally an operations/database change: no unauthenticated write endpoint was added.

The provider audits did not establish complete Forever statistics or defensible per-specialization weights. Therefore the migration seeds 27 specialization profiles with empty weights, marked provisional, and states why. It seeds nine class capability rows with unknown proficiencies. Those rows cannot confirm an item is eligible. No coefficients are asserted as official or validated. A profile with configured weights remains provisional until reviewed; its item score is labelled `provisional`.

## Interpretation limits

- A score compares one item at a time and only within one slot family.
- It does not prove the highest-score item is the optimal complete gear set.
- The initial formula does not evaluate effects/procs. Items with effects return incomplete.
- Weapon damage/speed and armor are available as numeric inputs, but require explicitly configured, documented weights (weapon speed can use a negative weight where an evidence-backed method supports it).
- No BIS labels, ranking of current catalog records, or level progression recommendations are produced.
- The algorithm identifier is `weighted-item-score-v1`; profile version is returned with every result for reproducibility.

## Examples (synthetic test fixtures only)

The unit tests use a clearly synthetic test sword with verified fixture data, Strength = 3, and a provisional Strength weight of 2. It produces `3 × 2 = 6`, status `provisional`, and a contribution row showing `3`, `2`, and `6`. The same fixture with unknown stat completeness or an empty profile returns no numeric score (`incomplete`). Production catalog entries are not modified by these tests.
