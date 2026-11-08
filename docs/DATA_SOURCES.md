# Data sources and attribution policy

## Current status (Phase 2)

No game data source is connected to the application. The review of TheWoWDB is captured in [DATA_SOURCE_AUDIT.md](DATA_SOURCE_AUDIT.md). Phase 1 recommended it for a limited catalog validation pilot, with reservations around required-level mismatches, field coverage, restrictions, acquisition sources, and licensing of icon assets.

The Phase 2 application does not request TheWoWDB, persist its records, or display item content. `scripts/explore_wowdb.py` remains a separately bounded research tool; it is not called by FastAPI or the frontend.

## Rules for a future provider adapter

- Keep each provider client isolated from the catalog domain and HTTP API. Normalize only fields supported by that provider, with source/version/build and observed time.
- Keep missing and contradictory values explicit. A null or empty field is not automatically proof that an item has no restriction.
- Never use Classic Era as a silent fallback for Forever. Any reference comparison must retain its own game/version identity.
- Record terms URL, attribution text, allowed uses, review date, and data coverage before enabling an adapter.
- Display required attribution next to provider data. Do not provide raw provider dataset downloads or bulk dumps.
- Do not cache, proxy, copy, or rehost item icons unless their applicable asset terms have been reviewed.
- Add tests using small, authorized fixtures and mocked HTTP responses. Do not put provider credentials in client-side variables.

## Current source decision

TheWoWDB remains a candidate for a controlled sample only. It is not approved as the sole source for gear eligibility or acquisition provenance. No provider adapter is implemented in Phase 2.
