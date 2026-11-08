# Forever Item Catalog Coverage Audit

**Audit date:** 7 November 2026 (America/Bogota). Live requests were made against TheWoWDB immediately before this report. The API build observed in the successful sample was `wow_classic_beta-1.60.1.70532`.

## Method and bounded results

Reviewed TheWoWDB's current [developer documentation](https://thewowdb.com/developers/) and the existing adapter/importer. Ran a dry-run against the documented Forever list and detail APIs. No database writes were performed for this audit, and no raw response archive was retained.

| Experiment | Retrieved from list | Detail validated | Detail failures | Persisted | Result |
|---|---:|---:|---:|---:|---|
| `import-items --limit 10 --dry-run` | 10 | 8 | 2 (IDs 41, 42 returned HTTP 404) | 0 | Completed; 32 field-quality issues across the 8 valid details. |
| `import-items --limit 100 --dry-run` | Incomplete | Incomplete | Request ended with a socket read timeout | 0 | No complete report; do not treat as a 100-item sample. |

The 8 successful details from the 10-item experiment were all weapons or armor, but covered only Main Hand, Two-Hand, Shirt, Legs and Feet. Shirt is outside Forever BIS's 17 planner slots. All 8 had empty `stats`, `effects` and `classes` arrays, and detail `required_level` was null. This is a small, first-page sample, not a coverage estimate for the provider's complete database.

The three existing database rows (IDs 25, 35, 36) remain unchanged and are still `needs_review`. Their list/detail required-level conflict and empty-array issues are unchanged. No records from the audit experiment were persisted.

## Endpoint inventory and observed scope

The current documentation lists these public, unauthenticated JSON routes:

| Route | Documented purpose | Equipment use and observed limits |
|---|---|---|
| `GET /api/v1/forever/item/?page=&per_page=&q=` | Paged Forever item summaries. | `per_page` 1–100; `page` 1–200; `q` is a case-insensitive name match up to 64 characters. No documented slot, quality, armor, weapon, required-level or item-level filters. The first-page list order is provider-defined and unsuitable as a diverse gear sample. |
| `GET /api/v1/forever/item/{id}` | Item detail. | Adds typed item/slot, armor/weapon objects, arrays for stats/effects/classes, and fields such as binding, sockets, vendor sell value, faction market prices and links. It does not document a drop/source relation. |
| `GET /api/v1/forever/search/?q=` | A few matching records across kinds. | The documented example is cross-kind search; it does not advertise equipment filters or a complete item search. A live `q=worn` request returned zero grouped results. |
| `GET /api/v1/tooltip/forever/item/{id}` | Rendered tooltip HTML plus plain fields. | A live request for ID 25 returned HTML and a `fields` object containing item fields, including stats/effects/classes. It supplied no additional populated stats for that item. The docs' example tooltip ID 12640 returned HTTP 404 on the current Forever route. The existing adapter deliberately rejects this route and does not ingest tooltip HTML. |
| `GET /api/v1/forever/quest/{id}`, `/npc/{id}`, plus paged quest/NPC routes | Generic Forever quest/NPC records. | May help manual cross-reference, but the documented item schema does not provide links to a quest, boss, vendor or drop record. No documented item-drop table or acquisition relation was found. |

The API docs say list records have `has_more` and `links.next`; a total may be omitted for large lists. Pages are capped at 200, so the documented contract does not promise an unlimited, complete traversal. The provider adapter follows a validated `links.next` link and can paginate when its requested limit spans pages. The importer itself is capped at 100; with its default `per_page=100`, it intentionally reads only page 1. This is a bounded-sample limit, not proof of a complete-catalog import. It does not expose `q` or equipment filters.

The 100-item dry-run did not finish because a socket `TimeoutError` escaped the adapter/import loop; the provider currently retries `URLError`, HTTP 429 and selected 5xx responses, but this observed socket timeout was not converted into a retryable `ProviderError`. Thus this run failed operationally, not as evidence that page 1 contained 100 complete details. This is a code limitation to resolve before larger unattended imports; no code was changed in this research phase.

## Existing importer behavior

- It takes the first `limit` IDs from the list, then fetches one detail per ID.
- It normalizes all valid item kinds and does not restrict the sample to wearable gear or target slots.
- It preserves list/detail conflicts as quality issues, and does not equate absent data with zero.
- It caps each run at 100 and is dry-run by default; explicit confirmation is required to write.
- It stores no raw provider response archive. The report is a sanitized summary.
- Its ETag cache is process-local, uses a one-hour expiry and sends `If-None-Match`; the provider docs specify one-hour public responses and five-minute tooltip responses (due to live AH price). Tooltip caching is not implemented in the adapter.
- The provider enforces a request interval of about 0.51 seconds and handles documented 429 `Retry-After`, selected 5xx and URL errors. Socket read timeout handling remains an observed gap.

## Coverage conclusion

TheWoWDB provides useful Forever identity and basic equipment structure, but the bounded evidence is narrow: the first 10 list IDs yielded 8 valid equipment details, two detail 404s, only four of the planner's relevant slot groups at most (Main Hand, Two-Hand, Legs, Feet; plus a non-planner Shirt), no non-empty stat/effect/class arrays and unresolved required levels. The first-page sequence is not a representative or diverse set. Current coverage cannot support reliable progression suggestions across 17 slots or levels 1–60.

Do not promote provider rows from `needs_review` automatically. Do not use missing stats/restrictions/sources as negatives and do not fill gaps with Classic Era.

## Reproducibility

From repository root with `.venv` configured:

```powershell
& .\.venv\Scripts\python.exe -m backend.app.ingestion.cli import-items --limit 10 --dry-run
```

This uses only documented list/detail routes, observes the adapter pacing, and makes no database writes. Results can vary as the provider changes. Recheck its live [terms, pagination and limits](https://thewowdb.com/developers/) before repeating or publishing data.

## Sources

- [TheWoWDB Developers: routes, schema examples, paging, cache, rate limits and terms](https://thewowdb.com/developers/)
- [Eternadex item database and stated data methodology](https://eternadex.com/en/datenbank/)
- [Eternadex About and sources](https://eternadex.com/en/ueber/)
- [Eternadex data contribution process](https://eternadex.com/en/beitragen/)
