# Patch identifiers and catalog snapshots

Patch IDs are internal Forever BIS identifiers. They are never inferred from a Wowhead item creation date or a provider build string. No patch records are currently seeded because none has been editorially established.

`ForeverPatch` supports `research`, `review`, and `published` status. An import may reference an existing internal patch ID; imports without one remain unassociated. `CatalogImportSnapshot` stores provider/build/query, request bound, start/end timestamps, per-outcome counts, quality counts, and resumable progress. Each item observation has an `ItemDataSnapshot` with raw provider payload, normalized observation, content hash, ETag, captured time, and changed-field list.

Change history is informational. There is no automatic recommendation publication or scoring-profile recalculation. A future patch publishing flow should compare snapshots, review affected fields, explicitly publish patch status, and separately decide whether to invalidate cached item scores.

Inspect through `GET /api/v1/patches`, `GET /api/v1/patches/{id}/imports`, and the paginated import/record routes. Raw JSON remains in the local database and is intentionally omitted from these read APIs.
