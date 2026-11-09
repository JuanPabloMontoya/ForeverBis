# Forever BIS — Agent guide

This file is the operating guide for future Claude/Codex sessions in this repository. The repository is the source of truth; verify the current database and Git state before relying on the historical project notes.

## Product boundary

Forever BIS is a level-by-level WoW Forever gear progression planner. The Gear Planner is the primary experience. The Item Database supports it. The project must never silently substitute Classic Era data, invent item statistics, or present an unverified item as a confirmed recommendation.

The current catalog contains provider observations, not a finished BIS dataset. Scoring profiles are provisional unless the database says otherwise. Empty, conflicting, or missing values stay unknown. A planner response with no confirmed recommendations is a valid safe result.

## Read first

Before changing code, read:

- `PROJECT_PLAN.md`
- `README.md`
- `docs/DATA_SOURCES.md`
- `docs/DATA_QUALITY_REPORT.md`
- `docs/GEAR_PLANNER.md`
- `docs/RECOMMENDATION_FLOW.md`
- the relevant focused document under `docs/`

For ingestion work also read `docs/CATALOG_IMPORT.md` and inspect the current Alembic revision and import-job status. Do not assume that an older report describes the current database.

## Architecture rules

- Keep the recommendation engine independent from FastAPI, SQLAlchemy and React.
- Keep provider adapters independent from catalog/domain models.
- Keep external API schemas separate from normalized database models.
- Keep raw provider payloads and provenance; normalization must be reversible/auditable.
- Eligibility runs before scoring. Unknown restrictions are not unrestricted.
- Scoring weights are data/configuration, not frontend logic or route-specific constants.
- Recommendations require verified data, known eligibility, available status and a complete score.
- Individual item ranking is not whole-set optimization.
- Wowhead is a manually verified link/reference only. Never scrape it.
- TheWoWDB is the authorized automated provider. Respect its documented pagination, pacing, ETags, retries and attribution.

## Data safety

Never run `docker compose down -v`, `docker volume rm`, `docker system prune`, `DROP TABLE`, `TRUNCATE`, or a database reset. Never rewrite the original catalog rows merely to make a test or recommendation appear populated. Use additive Alembic migrations and inspect the current revision before applying one.

Do not commit or push unless the user explicitly asks. Do not put credentials in source, frontend code, reports or documentation. Do not redistribute raw provider datasets; reports should contain aggregates and sanitized examples only.

## Common commands (PowerShell)

```powershell
# Start/stop local services; PostgreSQL is preserved by stop-dev.ps1
.\dev.ps1
.\stop-dev.ps1

# Database
python -m alembic current
python -m alembic upgrade head
python -m alembic check

# Backend quality
python -m pytest
python -m ruff check backend alembic tests
python -m ruff format --check backend alembic tests

# Frontend (use the installed npm path if npm is not on PATH)
Set-Location frontend
npm test
npm run typecheck
npm run build
Set-Location ..
```

The launcher does not apply migrations. Review and apply migrations explicitly.

## Full catalog importer

The full importer is resumable and separate from the bounded sample importer. It requires explicit confirmation and uses job `1` in the current local run:

```powershell
python -m backend.app.ingestion.full_catalog_cli status --job-id 1
python -m backend.app.ingestion.full_catalog_cli hydrate --job-id 1 --confirm-write
python -m backend.app.ingestion.full_catalog_cli report --job-id 1
```

Check status before starting another process. Enumeration is only complete when provider pagination says there are no more pages. Hydration is only complete when every discovered ID has a terminal recorded outcome. A 404 is a failed detail lookup, not proof that the summary item never existed. See `docs/CATALOG_IMPORT.md` for recovery and rate-limit details.

## Change workflow

1. Inspect `git status`, the relevant files, current migrations and database state.
2. Make the smallest change that satisfies the request.
3. Add deterministic tests for behavior and failure states.
4. Run the checks relevant to the change.
5. Update the focused documentation and `PROJECT_PLAN.md` only with verified facts.
6. Report what was implemented, what was tested, and what remains blocked.

Do not start a later product phase implicitly. If real provider data or authorization is insufficient, preserve the limitation and document it instead of weakening validation.
