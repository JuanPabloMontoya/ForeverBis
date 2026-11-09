# Forever BIS

Forever BIS is a WoW Forever level-by-level gear progression planner built with React/TypeScript and FastAPI. Its homepage is the Gear Planner prototype with character selectors, a selectable 1–60 progression strip, and a 17-slot equipment paper doll. Item Database is a secondary section backed by the Phase 3 bounded, source-aware catalog. Verified recommendations are not available, so the planner shows explicit unavailable states and never fills slots with invented gear.

Catalog data is supplied by TheWoWDB's documented Forever API, with visible attribution. Unknown and conflicting values remain unknown or under review. The local catalog has been enumerated from the full available list; detail hydration and field coverage are tracked separately. Imported rows do not automatically become verified, and the application does not silently substitute Classic Era data or redistribute provider datasets. See [the data quality report](docs/DATA_QUALITY_REPORT.md).

## Requirements

- Windows 10/11 with PowerShell 7 or Windows PowerShell 5.1
- Python 3.12 or newer
- Node.js 22.12 or newer and npm
- Docker Desktop with Docker Compose v2

## Setup (PowerShell)

Run from the repository root.

### 1. Configure local environment

```powershell
Copy-Item .env.example .env
```

`.env.example` contains local development settings. Use private credentials for any shared environment and never commit `.env`.

### 2. Install backend dependencies

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PowerShell blocks venv activation, invoke tools directly, for example `\.venv\Scripts\python.exe -m pytest`.

### 3. Install frontend dependencies

```powershell
Set-Location frontend
npm ci
Set-Location ..
```

### 4. Apply database migrations when needed

```powershell
python -m alembic upgrade head
python -m alembic current
```

The development launcher does not apply migrations. Review and run them explicitly when the schema changes. PostgreSQL data is held in a persistent named volume.

### 5. Start the whole development environment

```powershell
.\dev.ps1
```

The launcher checks Docker Desktop, starts the existing Compose `db` service, waits for PostgreSQL health, verifies SQLAlchemy connectivity, starts FastAPI and Vite in the background, and opens the planner in your browser. It does not delete or recreate database volumes. Startup logs and the app-process manifest are stored in the ignored `.dev-runtime/` directory.

Startup summary and URLs:

```text
PostgreSQL: HEALTHY
FastAPI:    RUNNING
Vite:       RUNNING
Frontend:   http://localhost:5173
API Docs:   http://localhost:8000/docs
```

The launcher requires `.venv`, `frontend/node_modules`, `.env`, and Node.js 22.12+. It discovers Node.js from PATH, a standard installation, or the WinGet package location. Ports 8000 and 5173 are checked; an unrecognized process is never stopped or replaced. Use `-NoBrowser` for headless validation.

If this Windows PowerShell session blocks local scripts, allow this process only, then launch:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\dev.ps1
```

This does not change the machine or user execution policy.

### 6. Stop app services

```powershell
.\stop-dev.ps1
```

This stops only FastAPI and Vite processes recorded by `dev.ps1`. PostgreSQL remains running and its volume is preserved. To stop PostgreSQL separately while preserving its data, run `docker compose --env-file .env stop db`.

## Environment variables

The launcher reuses `.env`; it does not duplicate credentials. Required settings are `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_PORT`, `DATABASE_URL`, `API_CORS_ORIGINS`, and `VITE_API_BASE_URL`. Copy `.env.example` once to create a local `.env`. Keep `.env` private and do not commit it. Only `VITE_` variables are exposed to browser code.

## Troubleshooting the launcher

- **Docker unavailable:** open Docker Desktop manually, wait until its engine is ready, then retry `.\dev.ps1`. The launcher does not install or reset Docker.
- **Port 8000 or 5173 occupied:** the script reports the owning process and PID, then exits without stopping it. Close that service yourself, or use `.\stop-dev.ps1` if it is the recorded Forever BIS instance.
- **Missing `.env`:** run `Copy-Item .env.example .env` once.
- **Missing Python environment:** follow backend dependency setup above.
- **Missing frontend dependencies:** run `npm ci` from `frontend`.
- **A service exits during startup:** inspect `.dev-runtime/fastapi.stderr.log` or `.dev-runtime/vite.stderr.log`. `stop-dev.ps1` preserves PostgreSQL.
- **Database health is not healthy:** confirm Docker Desktop is running and inspect `docker compose --env-file .env ps` and PostgreSQL health. The launcher does not apply or repair migrations.

## Bounded data import

Dry run (does not connect to the database or write):

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --dry-run
```

Confirmed write (maximum 100 records):

```powershell
python -m backend.app.ingestion.cli import-items --limit 10 --write
```

Type `IMPORT` when prompted. For explicit noninteractive use, replace `--write` with `--confirm-write`. A missing write flag defaults to dry-run. Read [CATALOG_IMPORT.md](docs/CATALOG_IMPORT.md) and [DATA_SOURCES.md](docs/DATA_SOURCES.md) first. The full-catalog workflow below preserves provider payloads locally and does not provide bulk dataset export.

## Full TheWoWDB Forever catalog

The full importer follows documented pagination until `has_more` is false, checkpoints each page, then hydrates every item ID with bounded workers and provider request pacing. All write commands require explicit `--confirm-write`; PostgreSQL is not reset.

Current live import status (8 November 2026, 20:48 COT): summary enumeration completed 193 pages / 19,257 IDs; job 1 detail hydration remains in progress (1,361 detail successes, 13 reused, 1,872 HTTP 404, 16,010 pending, one failed). Check `python -m backend.app.ingestion.full_catalog_cli status --job-id 1` before interpreting catalog detail coverage. Resume with `python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write`; regenerate the report after completion.

```powershell
# Enumerate all summary pages and note the printed job ID.
python -m backend.app.ingestion.full_catalog_cli enumerate --confirm-write --per-page 100

# Hydrate each discovered provider item ID.
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write

# Resume enumeration or hydration after interruption.
python -m backend.app.ingestion.full_catalog_cli enumerate --job-id 1 --confirm-write --per-page 100
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write

# Check status and write JSON plus Markdown reports.
python -m backend.app.ingestion.full_catalog_cli status --job-id 1
python -m backend.app.ingestion.full_catalog_cli report --job-id 1
```

`full --confirm-write --workers 2` runs both stages sequentially. The initial live run enumerated 193 pages and 19,257 unique IDs; detail hydration has its own checkpoint and status, so check the job report before treating it as complete.

## Tests and checks

From the repository root:

```powershell
python -m pytest
python -m ruff check backend alembic tests
python -m ruff format --check backend alembic tests
python -m alembic check
```

From `frontend`:

```powershell
npm test
npm run typecheck
npm run build
```

## API

- `GET /api/v1/items`: paginated and sortable listing; supports search, quality, equipment slot, required-level range, source, and verification filters.
- `GET /api/v1/items/{item_id}`: item detail, stats/effects/restrictions, source/build, field-level quality issues, attribution, and verified external links.
- `GET /api/v1/catalog/summary`: total count, counts by quality and verification state, last import, and active data sources.
- `GET /api/v1/catalog/coverage`: item counts by provider slot, required-level band, and verification status.
- `GET /api/v1/catalog/imports`: paginated import history; `/api/v1/catalog/imports/{id}/records` lists normalized outcomes without raw payloads.
- `GET /api/v1/patches`: internal patch identifiers and statuses; no fictional patches are created.
- `POST /api/v1/suggestions` and `GET /api/v1/suggestions/{id}`: submit a pending suggestion using a validated Forever item URL and check its status.
- `GET /api/v1/health`: application and database health.
- `GET /api/v1/scoring-profiles`: active class/specialization scoring profiles and their provisional/configuration state.
- `POST /api/v1/items/{item_id}/eligibility`, `POST /api/v1/items/{item_id}/score`, and `POST /api/v1/items/compare`: item-level eligibility and scoring contracts.
- `GET /api/v1/planner/recommendations`: per-slot planner results for class, specialization, faction, and level. It returns all 17 slots and only includes a primary recommendation when verification, availability, eligibility, and score are confirmed.

The Gear Planner is the homepage and uses backend profile and planner APIs. The secondary Item Database keeps its search and filters, page navigation, catalog summary, item detail, uncertainty labels, and TheWoWDB attribution. Scoring profiles still have empty provisional weights, and imported records are not automatically verified; therefore the live planner returns no confirmed recommendations. This is an expected safe state, not a complete gear list. See [the planner guide](docs/GEAR_PLANNER.md) and [recommendation flow](docs/RECOMMENDATION_FLOW.md).

There is no public administrative review endpoint because the repository has no real authentication. Local operators can inspect with `python -m backend.app.ingestion.review_cli pending`, then decide with `python -m backend.app.ingestion.review_cli decide <uuid> approved|rejected|needs_info --notes "..."`. Approval does not verify or import an item. Details: [community workflow](docs/COMMUNITY_CONTRIBUTIONS.md), [verification](docs/DATA_VERIFICATION.md), [patch snapshots](docs/PATCH_SNAPSHOTS.md).

## Repository map

- `backend/app/api/v1`: versioned FastAPI routes and response contracts
- `backend/app/catalog`: database-backed catalog queries
- `backend/app/ingestion/providers`: isolated provider HTTP client and response schemas
- `backend/app/ingestion/normalizers`: provider-to-catalog normalization
- `backend/app/ingestion/services`: bounded, idempotent import service
- `backend/app/models`: SQLAlchemy source, version, item and provenance models
- `alembic`: append-only database migrations
- `frontend/src`: catalog interface, API client and tests
- `docs/DATA_SOURCE_AUDIT.md`: Phase 1 source research
- `docs/CATALOG_DATA_MODEL.md`: catalog schema and provenance decisions
- `docs/DATA_QUALITY_REPORT.md`: bounded live sample findings

## Phase scope

The Prompt 1 scoring foundation provides configurable individual item weights, eligibility checks, explainable scoring, and same-slot comparison. The Prompt 2 planner aggregates those existing backend results into a level-by-level interface; it does not optimize a complete equipment set. No verified specialization weights or item evidence currently support live BIS recommendations. Community suggestions and review workflow are future work and are not implemented. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for phase status and [DATA_SOURCES.md](docs/DATA_SOURCES.md) for source limitations and attribution rules.
