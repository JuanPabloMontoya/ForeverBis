# Gear Planner

The Gear Planner is the home page. It lets a user configure a class, an active specialization profile, faction, and level 1–60, then presents a 17-slot character paper doll. The Item Database stays available from secondary navigation.

## Character flow

1. The client loads active profiles from `GET /api/v1/scoring-profiles` and uses the returned classes and specializations for the selectors. It does not maintain a second specialization list.
2. The user selects Alliance or Horde and a level. The level strip supports direct selection, previous/next controls, arrow keys, Home/End, and horizontal scrolling.
3. Every configuration change requests `GET /api/v1/planner/recommendations` with `class_name`, `specialization`, `faction`, and `level`. A pending request is cancelled when its configuration is superseded.
4. The response is rendered into 17 slots: Head, Neck, Shoulders, Back, Chest, Wrist, Hands, Waist, Legs, Feet, Ring 1, Ring 2, Trinket 1, Trinket 2, Main Hand, Off Hand, and Ranged.
5. Selecting a slot opens its planner result and a separate list of matching catalog records. Catalog records are labeled as records, not recommendations. Selecting a candidate or catalog row opens item details.

## Result states

- **Recommended:** backend response includes a scored candidate. The interface displays its item, score, and score explanation. The backend is responsible for the verification and eligibility gate.
- **Insufficient data:** the backend has candidates or profile context but cannot establish a recommendation. Explanations are shown, for example unknown eligibility, unverified item data, missing statistics, or provisional/unconfigured weights.
- **Unavailable:** the backend has no candidate evidence for that slot, or no eligible scored candidate can be established. The UI does not infer that no such game item exists.
- **Loading / error:** the planner indicates refresh activity and reports API errors while preserving an explicit non-recommendation state.

Item detail displays only recorded fields: quality, level, slot, availability, numeric armor/weapon facts when known, statistics, effects, restrictions, acquisition records, source attribution, and provenance. Empty statistics and restrictions are described as unavailable or unverified; they are not interpreted as zero or unrestricted. A Wowhead link is rendered only when the record is marked verified and has a stored URL.

## Current data limits

The live catalog now has 18 real records, all `needs_review`. No item statistics or acquisition relationships are currently persisted. All 27 active class/specialization scoring profiles have empty weight maps and are provisional. The current data therefore supports configuration, interaction, and honest unavailable/incomplete states, but it does not support a live verified recommendation. Synthetic verified examples exist only in isolated frontend tests.

When a user opens a slot, the detail panel separates planner results from raw catalog records and offers a **Suggest a better item** form. It captures the current class/spec/faction/level/slot and accepts only an HTTPS `www.wowhead.com/forever/item=<id>[/slug]` URL. Submission is pending review and cannot change catalog or recommendation data. An exact item/context duplicate is retained and marked for review.

## Responsive layout and navigation

The paper doll is composed from slot groups around a central character figure at wider widths and changes to a compact slot layout at narrow breakpoints. The level strip remains horizontally scrollable. The UI uses text/initial placeholders when an item icon is missing. The visual design uses project CSS and does not include Blizzard artwork.

Browser-based visual inspection was not available in this validation session. Responsive behavior is covered by CSS breakpoints and component rendering, but has not been certified in a real browser at device sizes.
