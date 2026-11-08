# Data sources and attribution

## Active provider

Phase 3 uses the documented TheWoWDB Forever item API as a bounded catalog provider. The adapter calls only the documented list and detail endpoints:

- `GET /api/v1/forever/item/?page={page}&per_page={count}`
- `GET /api/v1/forever/item/{id}`

The list response exposes `total`, `has_more`, `links.next`, and the current build where supplied. The adapter follows documented pagination links only after validating the HTTPS host and Forever item path. It uses detail records for normalization and does not assume list records contain full item detail. Current documentation sets `per_page` to 1–100, pages to at most 200, a 120 request burst followed by 2 requests/second, and `Retry-After` for HTTP 429. See [TheWoWDB Developers](https://thewowdb.com/developers/) for current endpoint documentation and terms.

The client sends `If-None-Match` when it has a cached ETag and honors HTTP 304. The current cache is in-memory and bounded to the documented one-hour cache lifetime; it is not a persistent dataset cache. Requests are paced to two per second and retry transient 429/5xx/network errors with bounded backoff.

## Terms and attribution

The published API terms reviewed for Phase 3 permit free use, including commercial use, with a visible link to TheWoWDB wherever its data is displayed. They prohibit reselling the raw dataset. Item cards and details link to the provider record and show TheWoWDB attribution. The project does not offer bulk data export. Terms should be rechecked before a new release or material change in use.

Provider permission does not automatically grant a separate license for icon assets. This implementation stores and displays provider-supplied icon URLs; it does not download or rehost icons. Recheck image asset terms before proxying or redistributing those assets.

## Data boundaries

- TheWoWDB is an external provider, not the catalog domain model. Provider schemas and normalization live under `backend/app/ingestion/providers` and `normalizers`.
- Every record carries provider identity, provider item ID, observed game version/build, capture timestamp, and verification status.
- Missing and contradictory values remain unknown or are represented as a review issue. Empty arrays are not treated as proof of no stats, effects, or restrictions.
- List/detail disagreement for `required_level` is preserved as a field-level quality issue; the normalized value is `NULL` until reviewed.
- Market prices are not treated as faction restrictions. No faction restrictions or acquisition sources are inferred from prices or empty fields.
- No Classic Era fallback is used.
- No provider raw response archive or full dataset is stored. The import report contains summary counts and issue metadata only.

## Wowhead links

The application does not scrape Wowhead or copy its content. `wowhead_url` is populated only from a small explicit Forever mapping allowlist for IDs 25, 35, and 36, previously checked against the Phase 1 audit and matched to the current provider name and item level. An unlisted ID or mismatch produces `NULL`. This is narrow URL mapping evidence, not an assertion that equal IDs have equivalent game data. Recheck mappings when provider records/builds change.

## Current suitability

TheWoWDB is suitable for a controlled MVP catalog and source adapter, not as the sole authority for character eligibility or acquisition provenance. In the initial bounded run it supplied three valid item records, but all three have unresolved required-level contradictions and unverified empty stat/effect/restriction arrays. See [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md) for the observed sample and limitations. No BIS or gear eligibility decision may be made from this data alone.
