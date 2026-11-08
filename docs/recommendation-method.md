# Recommendation method status

No BIS or gear recommendation method is implemented in Phase 2.

The `backend.app.recommendations` package is an architectural boundary only. It must remain independent of FastAPI, SQLAlchemy, provider clients, and frontend code. Later work may define pure domain inputs and outputs and an explicitly versioned method, but should not introduce statistical weights or ranking behavior until the game data and curation criteria have been reviewed.

Before recommendations are published, the project must decide what BIS means during leveling, how it differs from effort/accessibility labels, how unknown restrictions affect eligibility, how level context is represented, and what evidence/review is required. These questions are still open in `PROJECT_PLAN.md`.
