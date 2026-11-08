# Forever item catalog data model

The SQLAlchemy model is an internal, source-aware catalog. External response models are kept separate from these tables. Migration history is append-only; current catalog schema is revision `20261108_0005`.

## Entities

| Entity | Role and key constraints |
|---|---|
| `DataSource` | Provider identity, base/terms URLs, required attribution, license review status, last checked time. Name is unique. |
| `GameVersion` | Snapshot identity (`game_key`, optional `build`, observed time, source, current marker). The source/game/build tuple has a database unique constraint when build is non-null; for an unknown build, the importer explicitly queries `IS NULL` and reuses the existing snapshot on sequential imports. PostgreSQL's ordinary unique constraint permits multiple nulls, so simultaneous unknown-build imports would need stronger locking/uniqueness before parallel ingestion is enabled. |
| `Item` | Internal primary key is separate from `source_item_id`. References source and game snapshot. Unique `(source_id, source_item_id, game_version_id)` supports idempotent imports. Nullable fields preserve unknown quality, level, equipment types and links. `source_item_url` supports per-record attribution. Prompt 3 adds raw payload, ETag, import/refresh times, field provenance and data-quality status. |
| `ItemStat` | Explicit provider stat type and numeric value; cascades with item. |
| `ItemEffect` | Explicit effect type, optional description and spell ID; cascades with item. |
| `ItemRestriction` | Explicit restriction type/value and verification status; cascades with item. |
| `DataQualityIssue` | Field-level uncertainty code, explanation and observed values (JSON); unique per item/field/code and cascades with item. |
| `ScoringProfile`, `ClassCapabilityProfile` | Existing Prompt 1 scoring weights and class proficiency evidence; profiles are currently provisional/unknown. |
| `AcquisitionSource`, `ItemAcquisition` | Structured acquisition entities and item relations, with source/build and verification metadata. No relations were imported in Prompt 3 because the provider sample supplied none. |
| `ForeverPatch` | Internal patch identity/status; never inferred from a provider or Wowhead creation date. No patch rows are seeded. |
| `CatalogImportSnapshot`, `ItemDataSnapshot` | Bounded run metadata and immutable per-record raw/normalized observations, hashes, ETags, outcomes and change fields. |
| `ItemSuggestion` | User proposal keyed by UUID, planner context, Wowhead Forever item ID/URL, review status, duplicate flag and local reviewer decision. It is separate from catalog item data. |

Indexes support source/version lookup, item name, quality, inventory type, required level, verification status, snapshot history and suggestion review. Foreign keys use restrictive deletion for sources/versions and cascading deletion for item-owned observations. Planner/scoring profiles exist, but no published BIS recommendations are stored.

## Uncertainty and provenance

`Item.verification_status` distinguishes `imported`, `needs_review`, `verified`, and `rejected`. The importer sets `required_level` to `NULL` when list and detail disagree, and records both observations in `DataQualityIssue`. Empty source arrays are flagged because completeness is not established. Availability is explicitly `unknown` unless an authorized source supplies evidence. Auction prices are not imported as restrictions. Raw provider JSON is preserved locally in `Item` and per-run `ItemDataSnapshot`; it is omitted from public APIs and reports.

Each item relates to a `GameVersion` with `game_key=wow_forever`, provider build when returned, and observation timestamp. Provider item IDs remain separate from local primary keys. Wowhead URLs are nullable and populated only by the verified mapping allowlist documented in [DATA_SOURCES.md](DATA_SOURCES.md).

## Migrations

- `20261107_0001`: Phase 2 infrastructure checkpoint.
- `20261107_0002`: catalog/source/version/item/child/quality tables and indexes.
- `20261107_0003`: aligns catalog indexes with SQLAlchemy metadata by removing the redundant data source name index. No catalog rows were deleted or rewritten.
- `20261108_0004`: scoring profiles and class capability foundations (applied before Prompt 3 recovery).
- `20261108_0005`: additive item provenance, import/record snapshots, acquisition metadata and community suggestions. Applied to PostgreSQL without dropping catalog tables or rows.

Apply with `python -m alembic upgrade head`; compare model metadata with the database using `python -m alembic check`.
