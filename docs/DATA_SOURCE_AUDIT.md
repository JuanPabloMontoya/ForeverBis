# Forever BIS — TheWoWDB Phase 1 Data Source Audit

**Status:** Phase 1 research complete; recommendation is conditional approval for a limited catalog pilot.  
**Reviewed:** 2026-11-07 (America/Bogota)  
**Live API sample:** 3 list records and 3 corresponding detail records.  
**No complete dataset was requested or downloaded.**

## Executive recommendation

TheWoWDB is suitable as a **candidate initial provider for basic Forever item catalog fields**, subject to a controlled pilot. Its public API exposes a documented Forever item list, per-item detail records, build identifiers, item-page links, pagination, cache validators, rate-limit headers, and explicit attribution/usage terms.

It is **not yet validated as the sole MVP source** for a gear planner. In this small live sample, the list endpoint returned `required_level: 1` for IDs 25, 35, and 36, while each corresponding detail endpoint returned `required_level: null`. The details contain fields for stats, effects, and class restrictions, but the three starter weapons had empty arrays. Faction prices in the detail response describe AH price observations and are not faction restrictions. Acquisition sources were not present in the three records and are not listed among item response fields in the API documentation. These gaps and the level mismatch must be understood before publishing eligibility or acquisition claims.

**Recommended decision:** proceed only with a small, attributed, non-publicing catalog validation pilot; do not make this API the sole authoritative source for restrictions or acquisition sources, and do not use API records directly as BIS recommendations. Do not fill null/absent Forever fields from Classic Era.

## Endpoint inventory

The [TheWoWDB public API documentation](https://thewowdb.com/developers/) describes the following relevant unauthenticated GET routes:

| Endpoint | Use | Documented/observed notes |
|---|---|---|
| `/api/v1/forever/item/?page=1&per_page=50&q=` | Paginated Forever item summaries; `q` is optional name search. | Live call with `page=1&per_page=3` returned envelope fields `version`, `kind`, `build`, `page`, `per_page`, `q`, `count`, `total`, `has_more`, `links`, and `results`. Each result included `id`, `kind`, `version`, `name`, `quality`, `item_level`, `required_level`, and item-page/API/tooltip links. |
| `/api/v1/forever/item/{id}` | One Forever item detail. | Live checked for IDs 25, 35, 36. See observed schema and sample below. IDs are provider's Forever page IDs. |
| `/api/v1/tooltip/forever/item/{id}` | Rendered tooltip HTML plus plain fields. | Documented; not used by the exploration script or included in the sample because HTML is not needed for normalized catalog validation. |
| `/api/v1/forever/search/?q={term}` | Search hits across Forever record kinds. | Documented; not needed for the bounded item sample. |

The docs show equivalent `{version}/{kind}` routes for other kinds, including spells, quests, NPCs, zones, and sounds. Those are outside this item audit. The documented API base is `https://thewowdb.com/api/v1/`; no API key is required for these public routes.

### Observed item response shapes

The list response is an envelope with a `results` array. `links.next` contained a URL for page 2, `has_more` was true, and `total` was null for the sampled large listing. The list item records were brief summaries.

The detail responses were JSON objects containing, among other keys:

`id`, `kind`, `version`, `version_label`, `build`, `name`, `quality`, `item_level`, `required_level`, `item_type`, `item_subtype`, `slot`, `armor`, `weapon`, `stats`, `effects`, `classes`, `icon_url`, `links`, and `attribution`.

The inspected detail records also carried nullable or optional fields such as `armor`, `binding`, `flavor`, `item_set`, `socket_bonus`, `unique`, `sockets`, and `vendor_sell`. They also included `faction_prices` and `price`, which are market-scan data, not character restrictions; the sanitized sample deliberately omits both. The developer documentation gives a full example for a spell, not a formal exhaustive item detail schema, so the live item shape should be treated as observed rather than guaranteed.

## Field coverage matrix

Status describes what this endpoint/documentation review establishes, not completeness for every item.

| Requested field | Status | Evidence and limits |
|---|---|---|
| Item ID | **Available** | List and detail have integer `id`; both also identify `kind: item` and `version: forever`. |
| Item name | **Available** | List and detail have `name`; corresponding TheWoWDB page links include the item slug and ID. |
| Quality | **Available** | List and detail have values such as `common`. |
| Item level | **Available** | List and detail have `item_level`; sample value was 2 for all three. |
| Required character level | **Partially available** | Both response shapes have `required_level`, but live list values were 1 for all three tested IDs while detail values were null. The distinction between absent requirement and missing data is not established; do not use this field as a hard eligibility rule until reconciled. |
| Inventory slot | **Available** | Detail records have `slot` (observed `Main Hand` and `Two-Hand`). Coverage across every item/slot remains unmeasured. |
| Armor type | **Partially available** | Detail provides `item_type`/`item_subtype` and an `armor` object, but the sample was weapons (`armor: null`). A normalized cloth/leather/mail/plate field and its coverage were not verified. |
| Weapon type | **Partially available** | Detail provides `item_subtype` (for example, `One-Handed Sword`, `Staff`) and `weapon` damage/speed data. No separate `weapon_type` property was observed. |
| Stats | **Partially available** | Detail has a `stats` array, but it was empty on all three sampled items. Non-empty stat objects, complete stat coverage, and stat semantics were not validated in this sample. |
| Item effects | **Partially available** | Detail has an `effects` array, empty on all three sampled items. Non-empty effects and completeness were not validated. Tooltip route also provides rendered HTML, which should not be treated as a normalized schema. |
| Icon | **Available** | Detail has `icon_url` (sample URLs point to Blizzard's render host). Separate permission/redistribution terms for the image assets were not established here. |
| Class restrictions | **Partially available** | Detail has a `classes` array, empty on all three sample records. The API docs do not specify whether an empty array always means unrestricted versus unavailable; non-empty restrictions and this semantic distinction need validation. |
| Faction restrictions | **Not verified** | Details had `faction_prices` entries labeled Alliance/Horde, but these describe price-scan scope and must not be treated as equipment restrictions. No faction-requirement field was observed or documented. |
| Acquisition sources | **Not verified** | No source/acquisition field appeared in the three details, and the API docs do not list one in their documented item schema. Absence in this small sample does not prove no other route or page contains source information. |

## Pagination, cache, and request limits

According to the API documentation:

- `per_page` accepts 1–100 (default 50); `page` accepts 1–200.
- `q` is a case-insensitive name match up to 64 characters.
- Large listings may return `has_more` and `links.next` instead of a total; smaller results may include `total`.
- API responses are cacheable for one hour; tooltip responses are cacheable for five minutes.
- Responses carry an `ETag`. Clients can send `If-None-Match`; unchanged resources return HTTP 304 with no body.
- Per IP, the documented limit is a burst of 120 requests, refilling at 2 requests/second per server worker. HTTP 429 includes `Retry-After`; `X-RateLimit-Remaining` reports remaining capacity. The docs recommend caching.
- CORS is open and the API does not accept credentials. The exploration script uses plain unauthenticated HTTPS requests and does not attempt to evade access controls.

The delivered script imposes a hard maximum of 10 item details, defaults to 3, uses only documented list/detail endpoints, requests no credentials, and optionally persists ETags. It follows the documented page/per-page scheme and stops at the requested count or when `has_more` is false. A 429 is retried once after a bounded `Retry-After`; other HTTP/network failures are reported.

## Attribution and licensing considerations

The [published API terms](https://thewowdb.com/developers/#terms) say the API is free for commercial and non-commercial projects if a visible link to TheWoWDB (or the record's `links.html`) appears wherever data is shown. They prohibit reselling the raw data as a dataset. The API's records carry an attribution object and a link to TheWoWDB. TheWoWDB describes itself as a fan site and says game data and names belong to Blizzard; the API may change, with breaking changes under a new `/api/v2/`.

Operational implications:

- Show a visible attribution link for displayed provider data, preferably the record's `links.html` alongside a global TheWoWDB credit.
- Do not expose a bulk-download/export of the raw provider catalog or commit full responses/dumps. The sample in this repository is deliberately limited to three sanitized item records and omits auction price/faction-price observations and tooltip HTML.
- The API terms reviewed do not independently establish permission to redistribute/hotlink Blizzard icon assets. Before displaying icons, check the applicable Blizzard fan-content/image terms and favor provider-approved URLs without copying the image files.
- Re-check the live terms before production and record the review date. This is a technical source audit, not legal advice.

## Rate-limited exploration artifacts

The attached [sanitized sample](data-source-sample.json) was derived from one list request (`per_page=3`) and three item detail requests. The API returned build `wow_classic_beta-1.60.1.70532`. Auction prices, faction price data, volatile market observations, and tooltip HTML were excluded. The list/detail required-level disagreement is recorded above; the sample preserves detail values as returned and does not reconcile them by inference.

Run the exploration from the repository root with:

    python scripts/explore_wowdb.py --max-items 3 --per-page 3

Run the mocked tests with:

    python -m unittest discover -s tests

The script does not persist raw provider responses. It writes only an allowlisted subset of item fields, the requested attribution, build, and sample timestamp.

## Wowhead Forever compatibility

Wowhead has a [Forever-specific database namespace](https://www.wowhead.com/forever/database), separate from its Classic database. The common observed page form is `https://www.wowhead.com/forever/item={id}/{slug}`. Three sampled TheWoWDB detail IDs were checked against Forever pages:

| TheWoWDB Forever ID/name | Wowhead Forever page checked | Result |
|---|---|---|
| 25 — Worn Shortsword | [Forever item 25](https://www.wowhead.com/forever/item=25/worn-shortsword) | Same name and item level; Wowhead page identifies Forever. |
| 35 — Bent Staff | [Forever item 35](https://www.wowhead.com/forever/item=35/bent-staff) | Same name, item level, weapon range and speed in inspected Forever page. |
| 36 — Worn Mace | [Forever item 36](https://www.wowhead.com/forever/item=36/worn-mace) | Same name and item level in inspected Forever page. |

This verifies that the numeric IDs and Forever URL pattern agree for these three records, not that all item IDs map one-to-one or that Classic pages are equivalent. TheWoWDB item endpoint does not return a Wowhead URL. A future link resolver should use the Forever namespace and require a checked ID/name/version match; it must never fall back to a Classic Era URL based solely on matching numbers or names. No Wowhead database content should be copied into the provider sample.

## API limitations and open questions

1. The docs do not give an exhaustive item-specific schema; detail fields above were observed from live responses and can change.
2. `required_level` disagreed between list and detail for all three IDs tested. Resolve before using it for item eligibility.
3. Stats, effects, and class restrictions have fields, but useful non-empty examples and coverage were not exercised in this starter-item sample.
4. Empty arrays/nulls have not been proven to mean unrestricted/none rather than unknown.
5. Faction eligibility and acquisition sources are not validated by this API sample. The presence of market scan faction labels is unrelated to character faction restrictions.
6. Provider item data is tied to a build. The sample identifies a beta build; the script must be rerun and diffs reviewed after source/build changes.
7. A public item endpoint does not itself validate the live in-game state or guarantee every item/restriction/source is exposed.
8. API permission for showing data does not answer asset licensing for icons, or permit raw dataset resale.

## References

- [TheWoWDB public API documentation, endpoints, pagination, limits, ETag, and terms](https://thewowdb.com/developers/)
- [TheWoWDB Forever item database](https://thewowdb.com/wow-forever/item/)
- [Wowhead Forever database](https://www.wowhead.com/forever/database)
- [Wowhead Forever Worn Shortsword, ID 25](https://www.wowhead.com/forever/item=25/worn-shortsword)
- [Wowhead Forever Bent Staff, ID 35](https://www.wowhead.com/forever/item=35/bent-staff)
- [Wowhead Forever Worn Mace, ID 36](https://www.wowhead.com/forever/item=36/worn-mace)
