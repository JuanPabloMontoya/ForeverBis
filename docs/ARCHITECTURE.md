# Forever BIS architecture

## Purpose

Forever BIS is a React/FastAPI application for level-by-level WoW Forever gear progression. It presents a character configuration, a level selector from 1 to 60, and a 17-slot equipment paper doll. The catalog and scoring services support that experience; they are not a substitute for verified Forever data.

## Repository map

```text
backend/app/
  main.py                 FastAPI factory, lifespan, middleware and routers
  api/v1/                 Versioned HTTP contracts and route handlers
  core/                   Settings, logging and application concerns
  db/                     SQLAlchemy engine, sessions and declarative base
  models/                 Catalog, scoring, patch and operation persistence
  schemas/                Pydantic request/response contracts
  catalog/                Catalog queries and domain-facing read operations
  recommendations/        Eligibility, scoring and planner aggregation
  ingestion/              Provider clients, normalizers, import services and CLIs
  community/              Suggestion validation and review service layer
frontend/src/
  app/                    Application shell, navigation and top-level state
  api/                    Typed HTTP clients
  features/planner/       Gear Planner and paper-doll components
  features/catalog/       Supporting Item Database UI
  styles.css              Dark fantasy visual system and responsive layout
alembic/                   Ordered additive database migrations
scripts/                  Developer/research helpers
research/                 Non-production, bounded source investigations
```

## Runtime boundaries

```text
React/Vite
   │ typed HTTP requests
   ▼
FastAPI /api/v1
   ├── catalog routes ───────► catalog queries ─────► SQLAlchemy/PostgreSQL
   ├── planner routes ───────► eligibility + scoring + aggregation
   ├── scoring routes ───────► eligibility/scoring services
   └── operations routes ────► snapshots, coverage and suggestions

TheWoWDB API ─► provider adapter ─► external schemas ─► normalizer
                                             │
                                             ▼
                                    catalog + provenance tables
```

The frontend never calculates eligibility or item scores. FastAPI routes translate HTTP contracts and delegate to services. The scoring engine does not import FastAPI or SQLAlchemy; it consumes domain objects and profiles so it remains deterministic and testable.

## Backend layers

### API layer

The application is mounted under `/api/v1`. Important routes include:

- `/health`
- `/items` and `/items/{id}`
- `/catalog/summary`, `/catalog/coverage`, and import history routes
- `/scoring-profiles`
- `/items/{id}/eligibility`, `/items/{id}/score`, and `/items/compare`
- `/planner/recommendations`
- `/suggestions`

There is no public administrative approval route because the repository has no real authentication system. Local review is performed through `backend.app.ingestion.review_cli`.

### Domain services

`backend/app/recommendations/eligibility.py` evaluates level, slot, class, specialization, faction, race, armor and weapon constraints. It returns eligible, ineligible or unknown; unknown is intentionally not treated as eligible.

`backend/app/recommendations/scoring.py` applies the configured weighted model and returns contributions, missing inputs and provisional/incomplete state. `compare_items` only compares items from the same canonical slot. Planner aggregation groups candidates per slot and publishes a primary recommendation only when verification, availability, eligibility and score completeness are sufficient.

### Ingestion

Provider adapters speak in external response schemas. Normalizers convert those responses into domain values and quality issues. Import services persist both normalized fields and raw observations, with provider ID, build, ETag, timestamps and field provenance.

The full TheWoWDB workflow has two checkpoints:

1. Enumeration follows documented pagination and persists every page before marking it complete.
2. Hydration processes discovered provider IDs with bounded workers and global request pacing.

The current migration head is `20261108_0006`, which adds resumable full-catalog job/page/provider-observation state. The current full live run has completed summary enumeration but must be checked before assuming detail hydration is finished.

### Community contributions

`POST /api/v1/suggestions` stores a pending suggestion with planner context and a validated Forever Wowhead URL. It never mutates catalog data, scoring profiles or recommendations. Duplicate-looking submissions are retained and flagged. Approval through the local review service is not item verification.

## Persistence model

Core catalog entities:

- `data_sources` and `game_versions` identify provider/build provenance.
- `items` stores normalized catalog identity and fields.
- `item_stats`, `item_effects`, `item_restrictions` store structured details.
- `data_quality_issues` records uncertainty and conflicts.
- `acquisition_sources` and `item_acquisitions` model supported sources only.
- `forever_patches`, `catalog_import_snapshots` and `item_data_snapshots` support history.
- `full_catalog_import_jobs`, `full_catalog_import_pages` and `full_catalog_provider_items` support resumable enumeration/hydration.
- `scoring_profiles` and `class_capability_profiles` configure eligibility/scoring.
- `item_suggestions` stores community submissions independently from published catalog data.

The identity constraint for imported items is provider + provider item ID + game version. Internal database IDs must never be confused with provider IDs.

## Data trust states

The application distinguishes raw provider data, normalized data, manually verified data, scoring results and published recommendations. The normal catalog status values are `imported`, `needs_review`, `verified` and `rejected`; newly imported rows remain `needs_review` unless a separate verification process establishes evidence.

Missing values are nullable/unknown. Empty provider arrays are not proof that no stats or restrictions exist. Conflicting list/detail values are retained as quality issues and must not be silently resolved.

## Frontend flow

The Gear Planner is the homepage. Character class, specialization, faction and level are held in React state. A level change requests planner data without a full page reload. The response always describes all 17 slots; each slot can be recommended, provisional, incomplete or unavailable. Selecting a slot opens its detail panel. The Item Database remains a secondary navigation destination.

The UI must show attribution for provider-backed content, label uncertainty, and hide unverified external links. It must never fill empty slots with invented item names, stats, sources or scores.

## Operational invariants

- PostgreSQL is local development infrastructure managed by the existing Compose service and persistent named volume.
- `dev.ps1` starts Docker PostgreSQL, FastAPI and Vite; `stop-dev.ps1` stops only app processes it recorded.
- Migrations are additive and must be inspected before applying.
- Full imports are bounded by provider pagination and persisted checkpoints; no unbounded or parallel duplicate runs.
- Raw provider payloads are retained for audit but are not exposed as bulk exports.
- No Wowhead scraping or automated protected-content reuse.
- No recommendation is published from unverified records or provisional empty profiles.

## Known limitations

The current provider data does not yet support reliable confirmed BIS recommendations: many required levels, statistics, restrictions and acquisition sources remain unknown, and scoring profiles are provisional. The planner therefore correctly returns explicit unavailable/incomplete states. Complete set optimization, automatic patch publication and authenticated administrative review are future work.

For provider limitations and current measurements, use `docs/DATA_SOURCES.md`, `docs/DATA_QUALITY_REPORT.md`, `docs/CATALOG_IMPORT.md` and the generated reports under `docs/reports/`.
