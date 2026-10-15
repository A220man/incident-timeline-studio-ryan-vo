# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

evidence-tagging-and-bulk-triage

## Roadmap

### core-evidence-import — Preview and transactionally import evidence with UTC normalization

Status: done

Acceptance:
- Preview CSV, JSON array, and JSON Lines evidence before committing
- Normalize explicit offsets and named time zones to UTC without guessing
- Reject ambiguous local timestamps and malformed input rows atomically
- Deduplicate replayed evidence while tracking raw and canonical hashes

Implementation: `backend/app/services/normalization.py`, `backend/app/services/catalog.py`, `frontend/src/components/ImportPanel.tsx`

Tests: `backend/tests/test_domain.py`, `frontend/src/tests/import.test.tsx`

### correlation-and-rate-analysis — Explainable entity correlation, coverage gaps, and rate anomalies

Status: done

Acceptance:
- Extract IP, email, actor, and host entities from structured fields and messages
- Connect adjacent appearances of shared entities into explainable graph components
- Detect internal telemetry gaps between successive events by source
- Calculate MAD-based rate burst anomalies with robust Poisson scale fallback

Implementation: `backend/app/services/entities.py`, `backend/app/services/analysis.py`, `frontend/src/components/AnalysisPanel.tsx`

Tests: `backend/tests/test_domain.py`, `backend/tests/test_evaluation.py`

### analyst-decisions-and-export — Incident lifecycle, review decisions, audit log, and safe exports

Status: done

Acceptance:
- Create and update incidents with optimistic concurrency version checks
- Record per-event review decisions (relevant/benign) with analyst notes
- Maintain transactional audit log for all mutating actions
- Export sanitized CSV neutralizing spreadsheet formulas and structured JSON

Implementation: `backend/app/services/catalog.py`, `backend/app/services/export.py`, `frontend/src/components/Timeline.tsx`

Tests: `backend/tests/test_api.py`, `frontend/src/tests/api.test.ts`

### auth-sessions-and-oidc — OIDC authorization code PKCE login and server-managed sessions

Status: done

Acceptance:
- Support Keycloak OIDC authorization code login with PKCE and state verification
- Validate asymmetric ID tokens and enforce role-based access control (viewer/reviewer/admin)
- Issue revocable server sessions with CSRF protection on mutating requests
- Provide local-only demo mode restricted to loopback clients

Implementation: `backend/app/core/auth.py`, `backend/app/core/db.py`, `backend/app/main.py`

Tests: `backend/tests/test_oidc.py`

### advisory-guidance — Aggregate-only advisory guidance with LLM provider adapters

Status: done

Acceptance:
- Generate deterministic local triage recommendations grounded in aggregate stats
- Provide opt-in adapters for OpenAI, Anthropic, Gemini, and Ollama without raw log egress
- Enforce strict citation validation against aggregate evidence categories

Implementation: `backend/app/services/advisory.py`

Tests: `backend/tests/test_advisory.py`

### severity-filtering-and-review-export — Timeline severity filtering and complete review export

Status: done

Acceptance:
- Filter incident events by severity (critical, high, medium, low, info, debug, unknown) in backend API and frontend timeline
- Reject invalid severity filter parameters with validation errors
- Preserve analyst review notes and reviewer identity in exported timeline CSV
- Expose dynamic product version metadata from VERSION rather than hardcoding static version numbers

Implementation: `backend/app/api/routes.py`, `backend/app/services/catalog.py`, `backend/app/services/export.py`, `backend/app/core/config.py`, `backend/app/main.py`, `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/components/Timeline.tsx`

Tests: `backend/tests/test_api.py`, `backend/tests/test_domain.py`, `frontend/src/tests/api.test.ts`, `frontend/src/tests/timeline.test.tsx`

### component-subgraph-filtering — Connected component and entity subgraph filtering

Status: done

Acceptance:
- Filter timeline view to events belonging to a specific correlation component
- Highlight entity link paths directly on timeline items

Implementation: `backend/app/api/routes.py`, `backend/app/services/catalog.py`, `backend/app/services/analysis.py`, `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/App.tsx`, `frontend/src/components/Timeline.tsx`

Tests: `backend/tests/test_api.py`, `backend/tests/test_domain.py`, `frontend/src/tests/timeline.test.tsx`

### evidence-tagging-and-bulk-triage — Bulk review actions and multi-event triage tagging

Status: planned

Acceptance:
- Batch mark multiple matching events as relevant or benign in one transaction
- Support custom tag labels on reviewed events

