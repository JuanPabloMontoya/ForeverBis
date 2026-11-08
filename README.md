# Forever BIS

Forever BIS is a level-by-level gear progression planner for WoW Forever. Phase 2 establishes the executable monorepo foundation: a FastAPI service, a React/Vite interface, PostgreSQL development infrastructure, and the first migration checkpoint.

The UI is intentionally a placeholder. It contains no game item records, recommendations, stats, drops, or BIS calculations. The data source audit and its three-record sample are documented in `docs/DATA_SOURCE_AUDIT.md` and `docs/data-source-sample.json`.

## Requirements

- Windows 10/11 with PowerShell 7 or Windows PowerShell 5.1
- Python 3.12 or newer
- Node.js 22.12 or newer and npm
- Docker Desktop with Docker Compose v2

## Setup (PowerShell)

Run these commands from the repository root.

### 1. Configure local environment

```powershell
Copy-Item .env.example .env
```

The credentials in `.env.example` are for local development only. Change them for any shared environment, and never commit `.env`.

### 2. Create and install the Python environment

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

If PowerShell blocks virtual-environment activation, run the project commands using the interpreter directly, for example `.\.venv\Scripts\python.exe -m pytest`.

### 3. Install frontend dependencies

```powershell
Set-Location frontend
npm install
Set-Location ..
```

The direct frontend dependencies are exact-version pinned. `npm install` also creates `frontend/package-lock.json`; subsequent clean installs can use `npm ci`.

### 4. Start PostgreSQL

```powershell
docker compose --env-file .env up -d db
docker compose ps
```

PostgreSQL data persists in the named `forever_bis_postgres_data` volume. To stop the service while preserving data:

```powershell
docker compose down
```

To remove the local database volume as well, use `docker compose down --volumes`.

### 5. Apply migrations

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

The foundation migration records its revision and intentionally creates no game-domain tables.

### 6. Start the backend

In a PowerShell terminal from the repository root:

```powershell
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- Application metadata: <http://127.0.0.1:8000/>
- Health: <http://127.0.0.1:8000/api/v1/health>
- OpenAPI UI: <http://127.0.0.1:8000/docs>

The server starts even if PostgreSQL is down. The health response reports `status: degraded` and `database: unavailable` until the connection check succeeds.

### 7. Start the frontend

In another PowerShell terminal:

```powershell
Set-Location frontend
npm run dev
```

Open <http://localhost:5173/>. Vite reads the root `.env` but only exposes variables beginning with `VITE_`; the frontend health request uses `VITE_API_BASE_URL` and defaults to `http://localhost:8000`.

## Quality checks

From the repository root:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check backend
```

From `frontend`:

```powershell
npm test
npm run typecheck
npm run build
```

## Repository map

- `backend/app/api/v1`: versioned HTTP routes
- `backend/app/core`: configuration and structured logging
- `backend/app/schemas`: versioned API contracts
- `backend/app/db`: SQLAlchemy engine, session and metadata base
- `backend/app/catalog`, `recommendations`, `ingestion`: future domain boundaries with no Phase 2 behavior
- `alembic`: migration environment and empty foundation revision
- `frontend/src`: app shell, API health client, reusable level slider and tests
- `docs/adr`: architecture decision records
- `scripts`: bounded Phase 1 source exploration script

## Architecture and scope

This is a modular monolith. HTTP handlers depend on versioned Pydantic contracts and call infrastructure through explicit boundaries. The recommendation package is separate from FastAPI, SQLAlchemy and React. Source adapters have their own future package boundary and do not write directly into HTTP handlers. No catalog tables, item ingestion or recommendation logic are in this phase.

Read [PROJECT_PLAN.md](PROJECT_PLAN.md), [the Phase 1 audit](docs/DATA_SOURCE_AUDIT.md), [data source policy](docs/DATA_SOURCES.md), and [recommendation method status](docs/recommendation-method.md) for the current decisions and constraints.
