# Product development plan

Each round completes one feature or repair. Future items are planned, not implemented claims.

## Current round

export-tags

## Roadmap

### event-tags-persistence — Event tags persistence and UI display

Status: done

Acceptance:
- Tags stored in events table and returned by API
- Single event review accepts optional tags field
- Bulk review tags persisted to events table
- Tags displayed in timeline list view and review panel

Implementation: `backend/app/core/db.py`, `backend/app/services/catalog.py`, `backend/app/api/routes.py`, `frontend/src/types.ts`, `frontend/src/api.ts`, `frontend/src/components/Timeline.tsx`

Tests: `backend/tests/test_api.py`, `frontend/src/tests/timeline.test.tsx`

### continue-implementation — Continue implementation and resolve known failures

Status: planned

Acceptance:
- Run checks, fix failures, and implement the next planned feature

### export-tags — Export review tags in CSV/JSON exports

Status: in_progress

Acceptance:
- Tags included in CSV export
- Tags included in JSON export

Implementation: `backend/app/services/export.py`

Tests: `backend/tests/test_api.py`

### filter-by-tags — Filter events by tags in UI and API

Status: planned

Acceptance:
- API supports filtering events by tag
- UI adds tag filter to timeline controls
- Multiple tag filter support (AND/OR)

Implementation: `backend/app/api/routes.py`, `backend/app/services/catalog.py`, `frontend/src/components/Timeline.tsx`, `frontend/src/api.ts`

Tests: `backend/tests/test_api.py`, `frontend/src/tests/timeline.test.tsx`

