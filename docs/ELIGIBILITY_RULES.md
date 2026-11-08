# Eligibility Rules (Prompt 1)

Eligibility is evaluated separately from score calculation in `backend/app/recommendations/eligibility.py`.

## Outcomes

- **eligible**: all modeled checks have sufficient verified evidence and none excludes the character.
- **ineligible**: at least one verified condition excludes the character (for example, required level is higher, slot differs, or a verified class/faction/race restriction conflicts).
- **unknown**: evidence is missing, incomplete, or unverified. Unknown never means unrestricted.

## Checks

1. Character level must be 1–60; known required level must be met.
2. An item must have a recognized equipment family and match the requested family.
3. Item and eligibility verification must both be `verified`.
4. Verified class and specialization restrictions must match.
5. Verified faction restrictions must match Alliance/Horde selection. Faction market prices are not restrictions.
6. Race-restricted items require a race in the character request and a verified restriction.
7. Armor and weapon type eligibility requires a verified Forever class capability profile.

The database seeds all nine class capability rows as unknown with NULL armor/weapon lists. No Classic Era proficiency assumptions are copied. Provider `classes=[]` is not interpreted as unrestricted; records must have an explicit complete eligibility verification before a confirmed result.

## Slot mapping

The 17 display slots map to 15 comparison families because Ring 1/2 share Finger and Trinket 1/2 share Trinket. Main Hand, Off Hand, Ranged, and armor slots remain separate. Two-Hand inventory type is compared in the Main Hand family for candidate purposes only; this does not assert the complete equipment combination is legal.

## Restrictions and limits

Recognized restriction kinds are class, specialization, faction, and race. A restriction with non-verified status returns unknown unless a separate verified exclusion already proves ineligibility. Other requirements such as reputation, quest prerequisite, or proficiency encoded in an item restriction are not interpreted by this first version; their presence should keep item-level eligibility marked unknown until an appropriate rule exists.
