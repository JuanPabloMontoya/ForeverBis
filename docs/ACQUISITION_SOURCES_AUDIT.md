# Forever Item Acquisition Sources Audit

**Audit date:** 7 November 2026.

## TheWoWDB

The public API documents item, quest, NPC, zone and other records, plus generic cross-kind search and item tooltip routes. The tested item-detail contract exposes item fields and links to API/HTML/tooltip, but no documented drops, boss, quest-reward, vendor-stock, recipe, reputation or prerequisite relationship. Fields such as `vendor_sell`, AH `price` and `faction_prices` are not evidence of a vendor source, acquisition condition or faction restriction. Auction market faction pricing must never become an item restriction.

| Acquisition type | Documented TheWoWDB evidence | Audit status |
|---|---|---|
| Dungeon / raid drop | No documented item drop relation or encounter table. | Not available in the documented item API; no source verified. |
| Boss / NPC drop | NPC records exist, but no documented item-to-NPC loot relation. | Not available as a documented relation. |
| Quest reward / chain | Quest records exist, but no documented item-to-quest reward or prerequisite relation. | Not available as a documented relation. |
| Vendor purchase | `vendor_sell` is not a purchase listing; no documented vendor-stock relation. | Not available. |
| Profession crafting | No documented item-to-recipe relation in the Forever item API. | Not available. |
| Reputation | No documented item-to-reputation requirement/source relation. | Not available. |
| World drop / zone | Zone records exist, but no documented item-to-zone drop relation. | Not available. |
| Faction-specific acquisition | No documented relation; `faction_prices` are markets, not availability restrictions. | Not available. |
| Required quest / prerequisite | No documented item relationship. | Not available. |

The API's item list `q` is name search only; the generic `/forever/search/` route returns a few hits across kinds. Neither is documented as an acquisition search. Do not infer boss relationships, drop rates or prerequisites from names, item IDs or unrelated quest/NPC records.

## Eternadex

Eternadex says its item sources are assembled from a dungeon atlas and quest database. Its voluntary addon contribution workflow collects client observations including vendors and loot; the site says sufficient observations are required before showing drop percentages. This is the strongest publicly viewable acquisition lead found in this review. The source is still a mixture of game data, submitted observations and editorial/site data, and Eternadex warns that server changes can differ from client data. Public access and an embeddable tooltip do not grant an open dataset license. Use as a human research reference, or obtain written permission for automated data use and storage.

| Acquisition type | Eternadex public evidence | Reuse status |
|---|---|---|
| Dungeons / bosses | Database pages and dungeon atlas claim sources; 31 dungeon/raid entries listed on the current database page. | Publicly viewable; not approved for bulk extraction. Verify source/build and exact item relation manually. |
| Quests / prerequisites | Quest database claims rewards, objectives and quest chains. | Publicly viewable; no documented export API or data license found. |
| Vendors / world observations | Voluntary addon reports vendors, loot and locations. | Community observations; no authorized import contract identified. |
| Profession crafting | Site contains profession/recipe data, but this audit did not validate a complete item-to-recipe graph. | Manual research only pending permission and validation. |
| Reputation / faction | The public database has faction filters/sections; exact eligibility relation and completeness were not validated here. | Unknown; do not assume complete. |
| Drop rates | Site says percentages appear only after enough observations. | No rates imported or independently verified. |

## Other sources

- **Wowhead Forever:** public item pages and community comments may provide leads. No documented, authorized bulk item-source API was identified. Do not scrape or reuse protected page content; link only to individually verified pages.
- **Blizzard Developer API:** official APIs are available under their terms, but no official Forever item/acquisition resource was found in the current official documentation review. Do not probe undocumented endpoints. The terms prohibit unauthorized scraping/data mining and limit use to authorized API access.
- **In-game evidence:** a documented and permissioned player-reporting workflow could eventually verify drops, vendors and quest conditions, but would need evidence provenance, confidence, sampling, and review rules. No such Forever BIS workflow is implemented in this phase.

## Minimum source record for future use

Every acquisition assertion should identify Forever build, source item ID, source kind and exact source entity (quest, vendor, recipe, boss, zone), faction/class/rep/prerequisites where verified, source evidence URL or authorized observation, capture time, and verification status. Drop rate must remain null until a defined sample and method support it. A missing relation means unknown, not “world drop” or “no requirement.”

References: [TheWoWDB API docs](https://thewowdb.com/developers/), [Eternadex item database](https://eternadex.com/en/datenbank/), [Eternadex data contributions](https://eternadex.com/en/beitragen/), [Eternadex source/about statement](https://eternadex.com/en/ueber/), [Blizzard API terms](https://www.blizzard.com/es-es/legal/a2989b50-5f16-43b1-abec-2ae17cc09dd6/condiciones-de-uso-de-las-api-para-desarrolladores-de-blizzard).
