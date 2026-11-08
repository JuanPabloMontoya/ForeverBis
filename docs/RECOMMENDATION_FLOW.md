# Recommendation Flow

The client owns character configuration and presentation. FastAPI and the pure recommendation services remain authoritative for eligibility and scoring.

```text
class + specialization + faction + level
                 |
                 v
GET /api/v1/planner/recommendations
                 |
                 v
load active scoring profile, class capability profile, catalog candidates
                 |
                 v
compare_items() per equipment slot family
                 |
                 +--> eligibility and score states for each candidate
                 |
                 v
include primary only when score is complete, eligibility is eligible,
verification is verified, and availability is available
                 |
                 v
17 slot responses: recommended | insufficient_data | unavailable
```

The planner reuses the existing `evaluate_eligibility`, `score_item`, and `compare_items` services. It does not contain a parallel TypeScript scoring implementation. Ring 1/Ring 2 share the ring item family, and Trinket 1/Trinket 2 share the trinket family. Each slot gets the same per-family item ranking; choosing two distinct pieces across duplicate slots is not optimized in this prompt.

## Safety gates

A primary candidate is included only if all conditions hold:

- The score result is `scored` and has a numerical score.
- Eligibility is `eligible` for the configured character and requested slot.
- Catalog verification status is `verified`.
- Availability status is `available`.

Unknown eligibility, incomplete statistics, unknown availability, unverified records, missing weights, and provisional profiles cannot become confirmed recommendations. No unknown field is converted to zero or unrestricted. A profile with no weights produces an explicit insufficient-data explanation.

## Scoring and limits

Same-slot candidates use the backend comparison service. Alternatives and their score differences are returned only from the valid, comparable result list. The selected result is the highest individual score among candidates passing the gates above. This is not full set optimization and does not account for cross-slot stat caps, pair effects, unique-equipped constraints across the set, or the two-copy selection problem for rings/trinkets. The planner does not label these results official BIS.

The API response includes all 17 slot names, a slot-family identifier, state, optional recommendation, alternatives, counts, and explanations. It also includes profile version/provisional/configured metadata and the exact character context. The client uses that endpoint on each class, specialization, faction, or level change; it aborts an obsolete request to avoid applying stale data.

## Live verification state

At Prompt 3 validation, FastAPI reported healthy application/database status; the recommendation API returned 17 slots for Warrior/Arms/Alliance/level 20 and zero recommendations. The live catalog summary returned 18 items, all `needs_review`. The 27 scoring profiles remain provisional with no configured weights. These live results are why the empty planner is correct today.

Catalog snapshot changes are retained for review and comparison; they do not publish recommendations or trigger automatic scoring-profile changes. Community submissions are separate pending records. Approval records a moderator decision only and does not verify or import the suggested item.
