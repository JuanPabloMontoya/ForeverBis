# Forever BIS

Forever BIS is a WoW Forever level-by-level gear progression planner built with React/TypeScript and FastAPI. Its homepage is the Gear Planner prototype with character selectors, a selectable 1–60 progression strip, and a 17-slot equipment paper doll. Item Database is a secondary section backed by the Phase 3 bounded, source-aware catalog. Verified recommendations are not available, so the planner shows explicit unavailable states and never fills slots with invented gear.

Catalog data is supplied by the documented TheWoWDB Forever API, with visible attribution. Unknown and conflicting values remain unknown or under review. The initial live sample has three items and is not a completeness claim. See [the data quality report](docs/DATA_QUALITY_REPORT.md) before using the fields. The application does not silently substitute Classic Era data or redistribute provider datasets.

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

Type `IMPORT` when prompted. For explicit noninteractive use, replace `--write` with `--confirm-write`. A missing write flag defaults to dry-run. Read [CATALOG_IMPORT.md](docs/CATALOG_IMPORT.md) and [DATA_SOURCES.md](docs/DATA_SOURCES.md) first. No full-dataset import or raw dataset export is implemented.

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
- `GET /api/v1/health`: application and database health.

The Gear Planner provides class/spec/faction selectors, level navigation, equipment slots, and honest unavailable states. The secondary Item Database provides search and filters, page navigation, catalog summary, item detail, uncertainty labels, and TheWoWDB attribution.

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

Phase 3 establishes the item catalog and import pipeline only. No BIS engine, gear scoring, leveling recommendation, or class-specific equipment list has been implemented. See [PROJECT_PLAN.md](PROJECT_PLAN.md) for phase status and [DATA_SOURCES.md](docs/DATA_SOURCES.md) for source limitations and attribution rules.
