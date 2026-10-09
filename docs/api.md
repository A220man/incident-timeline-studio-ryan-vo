# API reference

All routes begin with `/api`. Session cookies authenticate requests. Obtain the CSRF token from `/auth/me`; send it as `X-CSRF-Token` for every mutation. Do not store session tokens in JavaScript storage.

## Authentication

- `GET /auth/mode`: configured login mode.
- `POST /auth/demo`: local-only demo session when explicitly enabled.
- `GET /auth/login`: redirect to the configured OIDC provider using S256 PKCE.
- `GET /auth/callback?state=...&code=...`: verify browser-bound state and signed identity; redirect to frontend.
- `GET /auth/me`: subject, username, roles, and CSRF token.
- `POST /auth/logout`: revoke session; returns 204.
- `GET /health`: public service/database liveness.

## Incidents and evidence

| Method / route | Request / response |
|---|---|
| `GET /incidents?limit=50&offset=0` | `{items, total}` with event and unreviewed counts; maximum page size 200 |
| `POST /incidents` | `{title, description}` → incident, 201 |
| `GET /incidents/{id}` | Full incident metadata and version |
| `PATCH /incidents/{id}` | `{title, description, status, version}`; status open or closed |
| `DELETE /incidents/{id}` | Admin-only cascade delete; 204 |
| `POST /incidents/{id}/import` | Multipart file, format csv/json/jsonl, timezone, epoch_unit seconds/milliseconds, commit true/false |
| `GET /incidents/{id}/events` | `{items, total, limit, offset}`; filters query, source, review_status; maximum page size 1000 |
| `PATCH /incidents/{id}/events/{event_id}` | `{status, note, version}`; status unreviewed/relevant/benign |
| `GET /incidents/{id}/analysis` | Entity inventory, temporal components/edges, observed gaps, rate buckets and alerts |
| `GET /incidents/{id}/history` | Import receipts and latest 200 audit entries |
| `GET /incidents/{id}/export?format=csv` | Download all incident events; use format=json for full evidence and default-parameter analysis |
| `POST /incidents/{id}/advice` | `{external, window_seconds, gap_seconds, bucket_seconds}` → mode, evidence, items, limitations, optional warning |

Analysis query defaults: `window_seconds=300`, `gap_seconds=900`, `bucket_seconds=60`. Positive bounded integers are required. A rate range exceeding 10,000 buckets returns an explicit range-too-large result rather than allocating unbounded memory.

Preview responses contain normalized events, row errors, duplicate count, input count, upload SHA-256, and `can_commit`. Preview does not persist anything. Commit reparses and revalidates the file in a transaction; any invalid row prevents persistence. Repeated files return the existing receipt with `replayed=true`. A receipt's duplicate count includes both repeated rows in that upload and events already in the incident.

Version conflicts return 409: refresh the incident/event and reconcile your change, then submit its current version. Never blindly overwrite after a conflict. Closing an incident prevents imports and event-review changes until reopened. The export includes all events regardless of browser filters; CSV neutralizes formula prefixes, while JSON preserves the original text.

## Error responses

Application errors use `{"error":{"code":"version_conflict","message":"..."}}`. Input-schema errors use FastAPI's `detail` array. Common statuses:

- 401: no valid session, expired login state, or invalid identity token.
- 403: insufficient role or invalid CSRF token.
- 404: missing incident/event, or disabled demo login.
- 409: stale version, closed incident, or unconfigured external advice.
- 413: upload exceeds configured size.
- 422: malformed import, invalid rows, incident limit, or schema validation failure.
- 503: unavailable or misconfigured identity provider.

External advice transport/parsing errors return local guidance plus a warning. Credentials and raw provider exception text are not returned.
