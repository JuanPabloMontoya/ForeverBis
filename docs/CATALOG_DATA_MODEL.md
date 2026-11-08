# Forever item catalog data model

The SQLAlchemy model is an internal, source-aware catalog. External response models are kept separate from these tables. Migration history is append-only; current catalog schema is revision `20261107_0003`.

## Entities

| Entity | Role and key constraints |
|---|---|
| `DataSource` | Provider identity, base/terms URLs, required attribution, license review status, last checked time. Name is unique. |
| `GameVersion` | Snapshot identity (`game_key`, optional `build`, observed time, source, current marker). The source/game/build tuple has a database unique constraint when build is non-null; for an unknown build, the importer explicitly queries `IS NULL` and reuses the existing snapshot on sequential imports. PostgreSQL's ordinary unique constraint permits multiple nulls, so simultaneous unknown-build imports would need stronger locking/uniqueness before parallel ingestion is enabled. |
| `Item` | Internal primary key is separate from `source_item_id`. References source and game snapshot. Unique `(source_id, source_item_id, game_version_id)` supports idempotent imports. Nullable fields preserve unknown quality, level, equipment types and links. `source_item_url` supports per-record attribution. |
| `ItemStat` | Explicit provider stat type and numeric value; cascades with item. |
| `ItemEffect` | Explicit effect type, optional description and spell ID; cascades with item. |
| `ItemRestriction` | Explicit restriction type/value and verification status; cascades with item. |
| `DataQualityIssue` | Field-level uncertainty code, explanation and observed values (JSON); unique per item/field/code and cascades with item. |

Indexes support source/version lookup, item name, quality, inventory type, required level, verification status, and child-item joins. Foreign keys use restrictive deletion for sources/versions and cascading deletion for item-owned child rows. No player-class, faction, acquisition, BIS, or scoring data is modeled in this phase.

## Uncertainty and provenance

`Item.verification_status` distinguishes provider-reported records from records needing review. The importer sets `required_level` to `NULL` when list and detail disagree, and records both observations in `DataQualityIssue`. Empty source arrays are flagged because completeness is not established. Availability is explicitly `unknown` unless a future authorized source supplies evidence. Auction prices are not imported as restrictions.

Each item relates to a `GameVersion` with `game_key=wow_forever`, provider build when returned, and observation timestamp. Provider item IDs remain separate from local primary keys. Wowhead URLs are nullable and populated only by the verified mapping allowlist documented in [DATA_SOURCES.md](DATA_SOURCES.md).

## Migrations

- `20261107_0001`: Phase 2 infrastructure checkpoint.
- `20261107_0002`: catalog/source/version/item/child/quality tables and indexes.
- `20261107_0003`: aligns catalog indexes with SQLAlchemy metadata by removing the redundant data source name index. No catalog rows were deleted or rewritten.

Apply with `python -m alembic upgrade head`; compare model metadata with the database using `python -m alembic check`.
