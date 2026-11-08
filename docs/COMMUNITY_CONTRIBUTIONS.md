# Community item contributions

## Public suggestion flow

The planner slot panel captures the current class, specialization, faction, level and slot, plus item name, a Wowhead Forever URL, optional explanation, and optional evidence text. The API accepts only HTTPS `www.wowhead.com/forever/item=<positive-id>[/slug]` URLs without query strings or fragments. The server does not fetch the URL.

Each submission receives a UUID, timestamp and `pending_review` status. A likely duplicate is identified by Wowhead item ID plus exact planner context; the duplicate is stored and linked to the prior suggestion for review, rather than dropped. `GET /api/v1/suggestions/{id}` exposes the submission's review status. Suggestions never mutate items, scoring profiles, or planner output.

## Administrative review

There is no real authentication in this project, so administrative actions are not exposed as public FastAPI routes and there is no enabled admin UI. Use the local operator CLI from the repository root:

```powershell
python -m backend.app.ingestion.review_cli pending
python -m backend.app.ingestion.review_cli decide <uuid> approved --notes "Identity and context checked"
python -m backend.app.ingestion.review_cli decide <uuid> rejected --notes "Does not match Forever item"
python -m backend.app.ingestion.review_cli decide <uuid> needs_info --notes "Please add a source reference"
```

The CLI records the current local OS username as reviewer identity and decision timestamp. Access to this command is limited to a trusted local project/database operator. Add a real authentication and authorization system before building an admin web interface or exposing review operations remotely.

Approval means only that a suggestion was accepted for follow-up. It does not import or verify the item and cannot change recommendations.
