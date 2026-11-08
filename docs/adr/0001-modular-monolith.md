# ADR 0001: Start with a modular monolith

- **Status:** Accepted for Phase 2
- **Date:** 2026-11-07

## Context

The project needs separate frontend, HTTP, persistence, source-data and recommendation responsibilities, but has no validated production-scale workload. Starting with multiple deployable backend services would add operational work without improving the initial boundaries.

## Decision

Keep one FastAPI backend and one React frontend. Maintain explicit Python packages for API, settings, database infrastructure, catalog, data-source ingestion, and recommendations. Keep the recommendation package independent of framework, ORM and provider packages.

## Consequences

- Local development and deployment begin with fewer moving parts.
- Module boundaries and contracts can be tested independently.
- A package can be extracted later if real load or ownership needs justify it.
