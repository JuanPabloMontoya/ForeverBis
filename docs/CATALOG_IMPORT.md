# Controlled TheWoWDB import

Run from the repository root after configuring `.env`, installing backend dependencies, and confirming PostgreSQL is reachable. The CLI is bounded to at most 100 summaries and defaults to dry-run. It uses only TheWoWDB's documented Forever API.

## Dry run

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --per-page 10 --search boots --dry-run --report $env:TEMP\foreverbis-dryrun.json
```

This fetches list summaries and documented item detail records, but does not open a database session. The report contains normalized, bounded field summaries and issue codes, not the raw provider payload.

## Confirmed write

Interactive:

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --per-page 10 --search boots --write
```

Type `IMPORT` at the prompt. For an explicitly approved noninteractive run use `--confirm-write` instead of `--write`. No write flag means dry-run. `--limit`/`--per-page` accept 1–100; provider pagination is followed only within its documented page limit.

## Retry and resume

- Transient HTTP 429 responses honor `Retry-After`; 5xx/network failures use a bounded exponential retry. Requests have explicit timeouts and are paced to the documented rate.
- A write creates a `CatalogImportSnapshot` before reading items. Each item result and resume checkpoint is committed independently. A process interruption leaves the snapshot `partial` with processed provider IDs.
- Inspect `GET /api/v1/catalog/imports` or query the `catalog_import_snapshots` table for the snapshot ID. Resume the same query with:

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --per-page 10 --search boots --resume-snapshot 12 --confirm-write
```

The original query, limit, and page size are taken from the persisted snapshot. Only snapshots marked `running` or `partial` can be resumed. Completed snapshots are not re-opened. Re-running a query creates a new snapshot; matching same-build items are skipped without detail requests, so it does not create duplicates or overwrite manual work.

## Reports and data handling

Reports distinguish fetched, imported, updated, skipped, failed, and `needs_review` counts. They include per-record normalized facts and validation issue codes. Raw response JSON is retained in the local PostgreSQL catalog and immutable `item_data_snapshots` for provenance; it is not returned by catalog APIs or written to JSON reports. Do not export or redistribute the provider dataset.

Every provider import remains unverified. Unknown required levels, stats, effects, class restrictions, acquisition sources, and conflicting values remain null/unknown and are recorded as quality issues. Empty arrays do not establish absence. Provider 404s are counted per item and do not roll back other successful records.

The adapter can call the documented item list/detail, cross-kind search, and item tooltip routes. Search is used only for bounded discovery. Tooltip HTML is not rendered or normalized as data. The documented API does not provide an item-acquisition relation in the imported item schema; no NPC/quest/vendor sources are fabricated. See [DATA_SOURCES.md](DATA_SOURCES.md) and [DATA_QUALITY_REPORT.md](DATA_QUALITY_REPORT.md).

## Local commands

```powershell
python -m backend.app.ingestion.cli import-items --limit 3 --search staff --dry-run
python -m backend.app.ingestion.review_cli pending
python -m backend.app.ingestion.review_cli decide <suggestion-uuid> needs_info --notes "Please provide evidence"
```

Review decisions are available only through the local CLI because no real authentication provider exists. Approval does not import or verify an item.

## Full catalog enumeration and detail hydration

The full-catalog CLI is separate from the bounded `import-items --limit` command. It uses only the documented Forever item list (`/api/v1/forever/item/`) and detail (`/api/v1/forever/item/{id}`) endpoints. It does not use search to approximate completeness and does not scrape Wowhead.

The provider documents at most 100 summaries per page and page numbers through 200. Pagination follows `links.next`, falling back to `page + 1` only when `has_more=true` and no next URL exists. It stops only when `has_more=false`; if page 200 still signals more results, the job is reported incomplete. Since `total` may be omitted, completeness uses pagination metadata. Requests are paced at about two per second across bounded detail workers; 429 honors `Retry-After`, and transient errors use bounded retries.

### PowerShell workflow

```powershell
python -m backend.app.ingestion.full_catalog_cli enumerate --confirm-write --per-page 100
python -m backend.app.ingestion.full_catalog_cli status --job-id 1
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write

# Resume the same job and stage after an interruption.
python -m backend.app.ingestion.full_catalog_cli enumerate --job-id 1 --confirm-write --per-page 100
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write

python -m backend.app.ingestion.full_catalog_cli report --job-id 1
```

`full --confirm-write --workers 2` combines enumeration and hydration. Each page's records and completion marker commit in one transaction. Item detail payloads, ETags, attempt timestamps, status, and failures persist per item. A 304 preserves stored detail data. A 404 is recorded as a detail failure, not as proof that a summary record never existed. Existing detail payloads for the same provider build are reused. Malformed summaries with a valid positive ID are retained as provider observations and sent to detail hydration; malformed entries without valid IDs are counted but cannot be safely assigned a catalog identity.

Summary-created catalog rows remain `needs_review`. Unknown fields remain unknown, and no statistics, restrictions, source, or verification are invented. The original three seed rows are preserved exactly; their API observations are stored in the separate provider-item records. Full list page payloads and per-item payloads are stored locally for traceability/cache revalidation. The reports contain aggregate counts only and must not be redistributed as the provider dataset.

The live enumeration completed 193 pages and found 19,257 unique IDs for build `wow_classic_beta-1.60.1.70532`. Detail hydration is a separate operation; check the job report for its current completion and failure totals.

## Full catalog live-run checkpoint (8 November 2026, 20:48 COT)

Job `1` completed list enumeration (193 pages; 19,257 unique IDs; build `wow_classic_beta-1.60.1.70532`) and is still hydrating detail. Latest report: 1,361 HTTP detail successes, 13 reused details, 1,872 HTTP 404, 16,010 pending, one failed (ID 2315, HTTP 200 name mismatch). The importer now preserves raw payload on validation conflicts; the failed row is to be retried after the active pass. Exact pending/failure IDs are in the JSON report.

```powershell
python -m backend.app.ingestion.full_catalog_cli status --job-id 1
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write
python -m backend.app.ingestion.full_catalog_cli report --job-id 1
```

All 19,257 catalog rows remain `needs_review`. A 404 is only a failed detail lookup, not an item deletion. Enumeration is complete; hydration is not.
