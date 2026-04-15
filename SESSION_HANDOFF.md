# DND VTT Session Handoff

This file captures implementation progress so a fresh chat can continue without redoing completed work.

## Current Status

- Overall roadmap status:
  - Phase 0: mostly complete.
  - Phase 1: substantial progress, not fully complete.
  - Phases 2-5: mostly not started.

- Approximate completion:
  - Phase 1: ~75-80%.

## What Is Implemented

### Command/Event/Realtime Foundation

- Revision-aware mutation flow with conflict handling.
- Command envelopes include:
  - `expected_revision`
  - `idempotency_key`
  - actor context (`actor_peer_id`, `actor_role`)
- Dispatcher layer:
  - `app/commands/dispatcher.py`
- Typed command contracts:
  - `api_contracts/commands.py`
- Event publishing abstraction:
  - `app/events/publisher.py`
- JSONL event log sink:
  - `app/events/file_event_log.py`
- Replay endpoint:
  - `GET /api/sessions/{session_id}/events/replay?after_revision=...`
- Frontend realtime sync:
  - replay on connect
  - buffered revision handling for out-of-order events

### Idempotency and Duplicate Suppression

- Duplicate command submissions with same idempotency key return cached results.
- Duplicate idempotent replays do not increment revision.
- Duplicate idempotent replays do not publish duplicate events to WS/log.

### Permissions/Roles/Ownership

- Roles supported:
  - `GM`
  - `AssistantGM`
  - `Player`
  - `Observer`
- Role assignment endpoint:
  - `POST /api/sessions/{session_id}/roles`
- Observer mutation attempts are denied (read-only role behavior).
- GM-secret read filtering implemented for selected surfaces:
  - notes/templates/session internals
- Actor ownership model implemented:
  - assign ownership endpoint:
    - `POST /api/sessions/{session_id}/actor-ownership`
  - non-GM actor/token mutations require ownership
  - state actor visibility filtered by ownership for non-GM
  - character list visibility filtered by ownership for non-GM

### Frontend Role-Aware Gating

- Role context plumbed through read/mutation API calls.
- Role selector added to app shell for local role simulation.
- UI gating added for major controls:
  - observer restrictions
  - GM/AssistantGM restrictions for GM tools/map edit actions.

## Must-Not-Break Invariants

- Backend is authoritative for game state mutations.
- Revision must be monotonic and increment exactly once per accepted mutation.
- Stale writes must return conflict (`409`) with current revision.
- Idempotent duplicates must:
  - return cached result,
  - not advance revision,
  - not emit duplicate events.
- Observer role must stay read-only.
- Non-GM/AssistantGM must not access GM-secret read surfaces.
- Non-owners must not mutate actors/tokens they do not own.

## Key Files Touched (High Signal)

- Backend:
  - `app/services/session_service.py`
  - `api/http_api.py`
  - `api/schemas.py`
  - `app/commands/dispatcher.py`
  - `app/policies/access_control.py`
  - `app/events/publisher.py`
  - `app/events/file_event_log.py`
  - `api_contracts/commands.py`
- Frontend:
  - `frontend/src/App.tsx`
  - `frontend/src/lib/apiClient.ts`
  - `frontend/src/realtime/sessionRealtime.ts`
  - `frontend/src/components/MapCanvas.tsx`
  - `frontend/src/components/MapToolsPanel.tsx`
  - `frontend/src/components/InitiativePanel.tsx`
  - `frontend/src/components/DMToolsPanel.tsx`
  - `frontend/src/components/CharacterImportPanel.tsx`
- Tests:
  - `tests/test_signaling_service.py`
  - `tests/test_realtime_ws.py`
  - `tests/test_command_dispatcher.py`

## Validation Commands

Run these after each logical chunk:

```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run build
```

## Remaining Phase 1 Work (Priority)

1. Centralize permission matrix (single evaluator used by all routes/services) to remove remaining ad hoc checks.
2. Expand object-level ACL/visibility coverage beyond current entities/surfaces.
3. Add deeper multiplayer correctness tests:
   - out-of-order sequences
   - duplicate delivery
   - concurrent edit race scenarios across more command types.
4. Complete frontend parity for all remaining role/ownership edge interactions.

## Recommended Next 3 Tasks

1. Introduce `app/policies/permission_matrix.py` with explicit `(role, resource, action)` rules and replace direct checks incrementally.
2. Add service/API-level permission guards for all read endpoints still lacking explicit matrix-based policy checks.
3. Add integration tests for matrix enforcement over:
   - session read,
   - state read,
   - characters read,
   - combat control,
   - map edit,
   - actor/token mutate.

## Suggested Prompt For New Chat

Use this exact prompt in a fresh thread:

> Continue implementation from `SESSION_HANDOFF.md`. Do not redo completed work. Prioritize finishing Phase 1 by implementing a centralized permission matrix and expanding policy coverage + tests. Run `ruff`, `pytest`, and frontend build after changes, and report updated Phase 1 completion percentage.

