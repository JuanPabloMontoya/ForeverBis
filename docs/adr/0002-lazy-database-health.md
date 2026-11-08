# ADR 0002: Keep application startup independent of PostgreSQL availability

- **Status:** Accepted for Phase 2
- **Date:** 2026-11-07

## Context

The backend must remain startable during local work when PostgreSQL is not running, while health output must report database reachability accurately.

## Decision

Create a SQLAlchemy engine without opening a connection during app construction. The health route performs a short-timeout `SELECT 1` check and returns an overall degraded status plus database-unavailable status when it fails. Database sessions are provided through a request dependency when future routes need them.

## Consequences

- OpenAPI and metadata remain available when PostgreSQL is down.
- The health endpoint makes a live DB check and may report degraded independently of process health.
- This phase does not add readiness/liveness orchestration policies beyond that response contract.
