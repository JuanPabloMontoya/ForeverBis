# Catalog verification workflow

## Status meanings

- `imported`: provider response normalized without the importer's current blocking issues. It is still not manually verified.
- `needs_review`: one or more important values are missing, conflicting, or ambiguous.
- `verified`: an authorized human review has confirmed the facts needed for use, with evidence and a review date.
- `rejected`: record is not acceptable for the Forever catalog.

The migration initializes older rows as `needs_review`. Provider import never assigns `verified`. Data-quality status is separate from a score and from recommendation publication.

## Field evidence

Imported rows store raw provider JSON in PostgreSQL, a normalized view, field-level provenance labels (`provider_supplied`, `unknown`, `conflicting`), import timestamps, and immutable per-run observations. Raw payloads are not returned by catalog APIs or report files. Values with provider/list conflicts remain NULL; empty arrays stay unknown. The model can label future manual evidence, but this phase does not implement a public editor for changing verified facts.

Review critical facts independently: identity/name, Forever build, slot, level requirement, stats/effects, class/race/faction and proficiency restrictions, and acquisition. Wowhead is a manual per-item reference only; do not scrape it or generalize IDs. The three existing Wowhead mappings remain on the original records only.

An item's approval as a community suggestion does not verify it. A separate data review must preserve evidence/provenance and explicitly update relevant statuses before it can be considered by the planner. Scoring profiles also need validated weights; verifying an item alone cannot produce a recommendation.
