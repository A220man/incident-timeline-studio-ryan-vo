# Changelog

## 1.4.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.3.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.2.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

## 1.1.0 — work-in-progress checkpoint

Partial code published for continued development. Known issues: STATUS.md.

- Add connected component and entity subgraph filtering: filter timeline to events in a specific correlation component via `/api/incidents/{id}/components` endpoint and component filter dropdown in UI.
- Add `Component` type and `ComponentsResponse` to frontend types; populate component dropdown from analysis correlation components.
- Add tests for component filtering in backend API and frontend timeline.
- Add `idx_events_severity` SQLite index for faster filtered queries on incident events.
- Preserve analyst review notes and reviewer identity in exported timeline CSV.
- Expose dynamic product version metadata from `VERSION` file for API and health endpoints.
- Add tests for severity filtering, validation, CSV review note preservation, and timeline UI filtering.

## [1.0.0] - 2026-10-09

- Add bounded CSV, JSON, and JSON Lines import with explicit epoch units, DST ambiguity rejection, UTC normalization, hashes, and replay-safe transactions.
- Add temporal/entity correlation explanations, observed source gaps, and robust event-rate analysis.
- Add incident lifecycle, version-conflict protection, analyst decisions, audit history, and spreadsheet-safe exports.
- Add OIDC PKCE login, signed identity-token validation, revocable server sessions, CSRF protection, and viewer/reviewer/admin roles.
- Add aggregate-only optional LLM advice with provider adapters and deterministic offline guidance.
- Add a seeded train/held-out evaluation that exposes shared-infrastructure false positives.
- Add a React/TypeScript dashboard and container deployment configuration.
