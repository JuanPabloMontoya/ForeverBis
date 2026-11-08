# Controlled catalog import

Run commands from the repository root after configuring `.env` and installing the backend. The importer is intentionally bounded and never launches a full-dataset import.

## Dry run (default)

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --dry-run
```

Dry run retrieves and validates records but does not create a SQLAlchemy engine or write to PostgreSQL. Omitting `--dry-run` also remains a dry run unless an explicit write option is supplied.

## Confirmed import

Interactive confirmation:

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --write
```

Noninteractive confirmation:

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --confirm-write
```

`--write` requires typing `IMPORT`. `--confirm-write` is an explicit confirmation flag intended for controlled automation. `--limit` and `--per-page` must each be between 1 and 100; they cannot trigger a full import. Optional `--report path.json` writes a sanitized validation/import summary, not raw provider responses.

## Processing and reports

The adapter requests list pages and documented detail records, uses the provider's Forever build when available, respects pagination and rate limits, and handles ETag/304. It validates provider data before normalization. Malformed records are reported as failures; uncertain fields become null or get `DataQualityIssue` records. A successful transaction upserts source/version/item identities and replaces child observations, so rerunning the same source/build does not duplicate items.

The summary reports retrieved, validated, persisted, created, updated, and failed counts, quality issue counts, source attribution metadata, and failed provider IDs. It does not preserve or expose the raw response dataset. Review `docs/DATA_QUALITY_REPORT.md` before treating any imported fields as authoritative.

Example bounded command:

```powershell
python -m backend.app.ingestion.cli import-items --limit 3 --confirm-write
```

This command writes only if the provider responds with valid records and the operator has explicitly confirmed. Check the database health endpoint first and ensure migrations are at head.
