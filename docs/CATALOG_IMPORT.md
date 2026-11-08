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
