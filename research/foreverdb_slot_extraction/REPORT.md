# ForeverDB slot-based equipment extraction

Research date: 2026-11-08  
Target: <https://foreverdb.net/items>  
User-Agent: `ForeverBIS-research/0.1 (+https://github.com/foreverbis)`

## Executive result

The proposed `?slot=<slug>&n=<total>` extraction method could not be validated against the public HTML interface. Requests for `slot=head`, `slot=Head`, `slot=1`, `slot=2h`, `slot=offhand`, `slot=ranged`, and `n=100` or `n=690` all returned the same server-rendered page: 100 featured item links and the generic text “All 21,152 items”. The query parameters were not reflected in the server-rendered response. No slot total was displayed, so no complete per-slot listing was downloaded.

This is a deliberate stop. Downloading `data/items.json` or executing the client-side loader would retrieve the entire item dataset, which is outside this bounded experiment. ForeverDB's robots file allows public pages but disallows `/api/`; the developer API requires an approved key.

## Public rules and reuse

- `https://foreverdb.net/robots.txt` allows `/items` and disallows `/api/`, `/auth/`, `/admin`, `/me` and other private paths.
- The developer page says the API is read-only, requires an API key, limits keys to 60 requests/minute and 10,000/day, and requires a visible link to ForeverDB wherever data is shown.
- The API rules prohibit reselling the data or presenting it as one's own. The page also states that client data is Blizzard's and ForeverDB is not affiliated with Blizzard.
- The public `llms.txt` says item pages identify their client build and extraction date, and that pages should be cited by URL.

Sources: [robots.txt](https://foreverdb.net/robots.txt), [ForeverDB developer API](https://foreverdb.net/developers), [ForeverDB items](https://foreverdb.net/items), [ForeverDB data guidance](https://foreverdb.net/llms.txt).

## Slot vocabulary discovered

The public item-list bundle defines these exact filter slugs and inventory-type mappings:

| Category | Display/filter slug | Inventory IDs observed in public bundle |
|---|---|---:|
| Armor | `head` | 1 |
| Armor | `neck` | 2 |
| Armor | `shoulder` | 3 |
| Armor | `back` | 16 |
| Armor | `chest` | 5, 20 |
| Armor | `wrist` | 9 |
| Armor | `hands` | 10 |
| Armor | `waist` | 6 |
| Armor | `legs` | 7 |
| Armor | `feet` | 8 |
| Accessories | `finger` | 11 |
| Accessories | `trinket` | 12 |
| Weapons | `1h` | 13, 21, 22 |
| Weapons | `2h` | 17 |
| Weapons/off-hand | `offhand` | 14, 23 |
| Weapons | `ranged` | 15, 25, 26, 28 |

The same bundle labels `1h`, `2h`, `offhand` and `ranged`; it does not expose separate `mainhand`, `shield` or `held-in-offhand` filter slugs. Shields and held-in-off-hand objects are represented within the `offhand` inventory group. One-hand weapons are represented within `1h`.

## Filter experiment

| Requested URL variation | HTTP | Response item links | Distinct IDs | Slot total displayed | Result |
|---|---:|---:|---:|---|---|
| `slot=head&n=100` | 200 | 100 | 100 | No | Filter not reflected in SSR |
| `slot=Head&n=100` | 200 | 100 | 100 | No | Same response |
| `slot=1&n=100` | 200 | 100 | 100 | No | Same response |
| `slot=2h&n=100` | 200 | 100 | 100 | No | Same response |
| `slot=offhand&n=100` | 200 | 100 | 100 | No | Same response |
| `slot=ranged&n=100` | 200 | 100 | 100 | No | Same response |
| `slot=head&n=690` | 200 | 100 | 100 | No | `n` not reflected in SSR |

The 100 links are the same featured list beginning with IDs 234819, 235044 and 284716. They are not evidence of a head-slot result set.

## Representative detail pages

Three publicly linked item pages were inspected, which is within the requested maximum for detail inspection. They expose stable numeric IDs, names, quality, item level, required level, slot/subtype, armor or stats where present, Forever-specific status text, source text and build/extraction date. The pages do not provide a complete source for every object: for the samples, acquisition is explicitly “not known yet”. The sanitized records are in [samples.json](samples.json).

Observed build: `1.60.1.70862`; extraction date shown by the site: `2026-11-08`.

## Coverage and quality result

| Measure | Result |
|---|---:|
| Slot totals | Not observable from public SSR page |
| Complete slot listings | 0 slots extracted |
| Unique equippable records extracted | 0 |
| Duplicate records | 0 observed; no slot dataset was obtained |
| Missing-field statistics | Not computed for a slot dataset |
| Detail pages inspected | 3 |
| PostgreSQL changes | None |

The site's public landing page reports 21,152 items, while `llms.txt` currently describes 23,243 client items. This is a site/build snapshot inconsistency and further supports recording the build/date with any future authorized extraction.

## Comparison with current TheWoWDB catalog

The existing Forever BIS catalog has 19,257 TheWoWDB summary records from the documented API enumeration, all `needs_review` at the current checkpoint. TheWoWDB provides a machine-readable list/detail API with pagination and provider IDs, but the current detail coverage is partial and many normalized stats, restrictions and acquisition relationships are unknown.

ForeverDB's three manually inspected HTML pages were richer in human-readable presentation: they showed armor, stats, required level, item level, slot, Forever-specific labeling and a build date. However, the public HTML did not expose a usable filtered result count or complete slot listing, and automated API access requires an approved key. The sources therefore cannot be merged automatically from this experiment.

## Recommendation

Do not implement this slot-based scraper or use it as a production ingestion method. The public page is suitable for manual verification and links. A complete equipment database would require either:

1. an approved ForeverDB API key and an authorized API extraction plan using its documented `limit`/`offset` interface; or
2. explicit permission for a bounded export with stable terms and attribution.

Until that authorization exists, continue treating TheWoWDB as the only automated provider and keep ForeverDB as a manual reference. No production data, migrations, frontend code or PostgreSQL records were changed.
