# ADR 0003: Keep the first migration free of game-domain tables

- **Status:** Accepted for Phase 2
- **Date:** 2026-11-07

## Context

Phase 1 found unresolved source coverage and a required-level discrepancy. Creating catalog tables now could prematurely encode uncertain field semantics.

## Decision

Install Alembic and SQLAlchemy metadata infrastructure and commit an empty foundation migration. Defer game catalog and recommendation tables until the data contract is reviewed in a later phase.

## Consequences

- Migration upgrade establishes revision tracking without implying unvalidated data semantics.
- The initial migration can run successfully against PostgreSQL while leaving `alembic_version` as the only migration-managed table.
