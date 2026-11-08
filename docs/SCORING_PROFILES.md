# Scoring Profiles (Prompt 1)

The database migration seeds one active profile for each of 27 current class/specialization pairs across the nine WoW Classic classes. A partial unique index permits only one active version per pair while retaining inactive historical versions. Each seed row uses version `v1-provisional`, `provisional=true`, an empty `stat_weights` map, and an explicit statement that no validated Forever specialization weights are available. Therefore these seed rows do not currently yield numeric scores.

Profiles contain optional role, version, active flag, assumptions, `stat_weights` keyed by canonical statistic name, and a reserved `adjustments` map. Example shape (illustrative configuration, not an authoritative game profile):

```json
{
  "class_name": "Warrior",
  "specialization": "Arms",
  "version": "reviewed-profile-version",
  "provisional": true,
  "stat_weights": {"strength": 0.0},
  "adjustments": {}
}
```

The example's numeric value is only a schema illustration, not a suggested weight. Configure weights only through a reviewed change with evidence and recorded assumptions. If validated weights eventually exist, create a new profile version rather than silently changing the meaning of prior calculations. The current API is read-only; it exposes profiles but does not provide unauthenticated weight editing.

All nine class capability rows start unknown. They are eligibility data, not scoring profiles, and must be reviewed against WoW Forever rules before being used.
