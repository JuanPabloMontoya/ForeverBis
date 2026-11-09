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

## Full catalog enumeration (8 November 2026)

The [official developer documentation](https://thewowdb.com/developers/) specifies public JSON endpoints, `per_page` 1–100, `page` 1–200, optional `total`, `has_more` and `links.next`, cacheable responses with ETags/304, and a burst/refill rate limit. The full importer follows pagination metadata, stores page ETags and responses, uses conditional revalidation where available, honors `Retry-After`, and conservatively paces requests. The terms require visible attribution and prohibit reselling raw data.

The live summary enumeration completed 193 pages: 19,257 summaries and 19,257 unique Forever item IDs, with zero duplicate or invalid entries. The reported build was `wow_classic_beta-1.60.1.70532`. This verifies enumeration of the API view observed on 8 November 2026; it does not imply detail hydration or BIS data coverage is complete.

## Data boundaries

- TheWoWDB is an external provider, not the catalog domain model. Provider schemas and normalization live under `backend/app/ingestion/providers` and `normalizers`.
- Every record carries provider identity, provider item ID, observed game version/build, capture timestamp, and verification status.
- Missing and contradictory values remain unknown or are represented as a review issue. Empty arrays are not treated as proof of no stats, effects, or restrictions.
- List/detail disagreement for `required_level` is preserved as a field-level quality issue; the normalized value is `NULL` until reviewed.
- Market prices are not treated as faction restrictions. No faction restrictions or acquisition sources are inferred from prices or empty fields.
- No Classic Era fallback is used.
- Full provider payloads are stored locally only where the approved full-catalog import workflow requires provenance and resumable ETag caching. No raw payloads are returned by public APIs or included in coverage reports; raw data is not sold or redistributed.

## Wowhead links

The application does not scrape Wowhead or copy its content. `wowhead_url` is populated only from a small explicit Forever mapping allowlist for IDs 25, 35, and 36, previously checked against the Phase 1 audit and matched to the current provider name and item level. An unlisted ID or mismatch produces `NULL`. This is narrow URL mapping evidence, not an assertion that equal IDs have equivalent game data. Recheck mappings when provider records/builds change.

## Current suitability

TheWoWDB is suitable for a controlled MVP catalog and source adapter, not as the sole authority for character eligibility or acquisition provenance. In the initial bounded run it supplied three valid item records, but all three have unresolved required-level contradictions and unverified empty stat/effect/restriction arrays. See [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md) for the observed sample and limitations. No BIS or gear eligibility decision may be made from this data alone.

## Phase 3.1 provider review (7 November 2026)

The current docs also list a public cross-kind search route (`/api/v1/forever/search/?q=`) and a rendered item tooltip route (`/api/v1/tooltip/forever/item/{id}`). Neither adds documented slot/quality/level list filters. The item-detail contract has fields for stats, effects and class restrictions, but the first 10 summaries' 8 valid gear details had all three arrays empty. Tooltip ID 25 returned an empty stats field; the docs' sample tooltip ID 12640 returned 404 in the current Forever API. The adapter remains restricted to documented Forever item list/detail paths; no ingestion changes were made.

The documented API cap is 100 results/page and 200 pages, with `has_more` and `links.next`; large-list `total` may be absent. The importer cap is 100 and the default per-page size is 100, so a default bounded run reads one page and is not a full catalog job. It takes the first IDs and does not filter for wearable types or slot diversity. A 10-item dry-run completed (8 valid, 2 detail 404s, 0 writes); the 100-item dry-run ended with a socket read timeout and produced no complete report. See [CATALOG_COVERAGE_AUDIT.md](CATALOG_COVERAGE_AUDIT.md).

Current provider choice is **hybrid with authorized complementary evidence and editorial verification**. TheWoWDB remains useful for a basic attributed item record. Eternadex is a human cross-reference: it publicly states that stats use Forever beta client data and acquisition sources use its dungeon atlas/quest database, but no public bulk API or explicit underlying-data reuse license was found. Its tooltip embed license is for displaying the provider's own script, not raw dataset extraction. Wowhead is only a page-link verification source, not an authorized ingestion API identified by this audit. Blizzard's official API terms allow authorized API use, but no documented Forever catalog endpoint was found. Do not scrape or silently substitute other game versions.

Additional endpoint inventory, field-level limits, attribution and usage status are recorded in [PROVIDER_COMPARISON.md](PROVIDER_COMPARISON.md), [ITEM_STATISTICS_AUDIT.md](ITEM_STATISTICS_AUDIT.md) and [ACQUISITION_SOURCES_AUDIT.md](ACQUISITION_SOURCES_AUDIT.md). The class/level/slot gap is in [LEVELING_COVERAGE_MATRIX.md](LEVELING_COVERAGE_MATRIX.md).

## Phase 3.2 comparison (7 November 2026)

This comparison covers only **Wowhead Forever** and **TheWoWDB Forever**. Wowhead pages and the Item Finder expose useful manual fields and per-item links, but the public tooltips/XML page is not a Forever-specific bulk API contract, and Wowhead/Fanbyte terms restrict crawler/agent downloading absent authorization. Use pages for manual verification and external links only. TheWoWDB remains the structured source suitable for attributed local records, but the prior 10-summary sample had only 8 valid details, unresolved level conflicts and empty stats/effect/class arrays; current 30-item list/detail requests timed out before producing a complete report. No current phase data was imported. See [Wowhead Forever audit](WOWHEAD_FOREVER_AUDIT.md), [TheWoWDB Forever audit](TWOWDB_FOREVER_AUDIT.md), [two-provider comparison](PROVIDER_COMPARISON.md) and [updated leveling matrix](LEVELING_COVERAGE_MATRIX.md).

Recommendation: **restricted hybrid**—TheWoWDB for fields available through its documented, attributed API; Wowhead for manual cross-checks and explicit Forever links. This is not enough to publish a reliable level-by-level catalog. Do not automate Wowhead extraction or fill TheWoWDB gaps with other game-version data.

## Prompt 3 current implementation (8 November 2026)

The adapter now allows the documented item list with optional `q`, item detail, cross-kind Forever search, tooltip, NPC, and quest paths. Production import uses list `q` and item detail; it does not use Wowhead automation. Pagination, ETags/304, one-hour response cache (tooltip five minutes), 0.51-second request pacing, explicit timeouts, bounded retries, and per-record HTTP failure handling are implemented. Search results are discovery only; detail 404s are recorded as failures.

The earlier controlled sample contained 18 catalog rows: the three original rows and 15 newly imported TheWoWDB records. Those historical rows were all `needs_review`; the current full-catalog enumeration and hydration totals are documented below and in the generated job report. The current API schema does not provide a verified item-to-NPC/quest/vendor/crafting relation, so none was persisted. Tooltips are available on the adapter but are not treated as authorization to copy protected HTML.

See [the current quality report](DATA_QUALITY_REPORT.md) for the exact import totals, slot/level coverage, 404s, and original-record integrity check. The new write workflow and safe resumption commands are in [CATALOG_IMPORT.md](CATALOG_IMPORT.md). Historical sample results above remain historical and should not be read as the current database state.

## Full catalog live status (8 November 2026, 20:48 COT)

The documented Forever list reached `has_more=false`: 193 pages, 19,257 unique IDs, build `wow_classic_beta-1.60.1.70532`. Detail hydration remains active at 1,361 HTTP successes, 13 reused payloads, 1,872 HTTP 404, 16,010 pending and one recorded name-conflict failure. Request pacing follows the documented approximate two requests/second sustained rate. Do not describe details as fully hydrated until pending IDs have outcomes and the final report is regenerated. Every record remains `needs_review`.
