# DND VTT Session Handoff

This file captures implementation progress so a fresh chat can continue without redoing completed work.

## Current Status (Latest)

- Phase 1 (chat, dice, presence, pings, GM feature flags) is implemented in worktree `feature/phase1-heartbeat` at `.worktrees/phase1-heartbeat`.
- Full verification in worktree passed:
  - `python3 -m pytest -q`
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test`
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" run build`
- Phase 1 Task 1 foundation is implemented in worktree `.worktrees/phase1-heartbeat`.
- Session-level Phase 1 feature flags now have default config wiring and SessionService helpers in that worktree.
- Desktop app launch path is functional via `bash scripts/run_desktop.sh`.
- Electron starts frontend + backend child processes and readiness checks pass.
- Session host/join flow works in desktop mode with token-auth context propagation.
- Realtime WebSocket sync is stable in desktop smoke runs.
- Phase 1 UX restructure baseline is now implemented (map-centered shell, drawer/tray, status rail, role policy, responsive modes, telemetry hooks).
- Phase 2 UX baseline is now implemented (token quick HUD, combat-map focus link, command palette scaffold, shortcuts overlay).
- Role-based onboarding overlays are implemented with skip/replay and per-role persistence.
- Fog re-hide is now persisted end-to-end via backend `hide-cell` command/endpoint.
- Realtime session-switch churn is reduced by reconnect/auth-context hardening in websocket client logic.

## What Was Implemented Across Recent Sessions

### Desktop/Electron Integration and Runtime Fixes

- Electron workspace added and wired:
  - `desktop-electron/package.json`
  - `desktop-electron/main.js`
  - `desktop-electron/preload.js`
  - `scripts/run_desktop.sh`
- Desktop bridge + readiness/status integration:
  - `frontend/src/lib/desktopBridge.ts`
  - `frontend/src/main.tsx`
  - `frontend/src/App.tsx`
- API/realtime desktop behavior stabilized:
  - CORS preflight support in backend.
  - Token-auth context propagation fixes for host/join.
  - WebSocket runtime dependency + desktop smoke validation.

### UX Phase 1 Delivered (Docs + Shell Baseline)

- Added full UX docs package:
  - `docs/ux/information-architecture.md`
  - `docs/ux/interaction-model.md`
  - `docs/ux/onboarding-flows.md`
  - `docs/ux/phase-plan.md`
  - `docs/ux/wireframes.md`
  - `docs/ux/implementation-tickets.md`
- Implemented shell layout foundation:
  - `frontend/src/components/layout/AppShell.tsx`
  - `frontend/src/components/layout/RightDrawer.tsx`
  - `frontend/src/components/layout/BottomTray.tsx`
- Implemented persistent status rail:
  - `frontend/src/components/StatusRail.tsx`
- Added role/status policy + telemetry primitives:
  - `frontend/src/lib/uxPolicy.ts`
  - `frontend/src/lib/uxTelemetry.ts`
  - `frontend/src/lib/uxPolicy.test.ts`

### UX Phase 2 Baseline Delivered

- Token quick-action HUD near selected token (player-smaller, GM-expanded):
  - `frontend/src/App.tsx`
  - `frontend/src/components/MapCanvas.tsx`
- Combat tray to map focus integration:
  - click combatant in initiative to focus token on map.
  - `frontend/src/components/InitiativePanel.tsx`
  - `frontend/src/lib/combatUtils.ts`
  - `frontend/src/lib/combatUtils.test.ts`
- Command palette scaffold and shortcut overlay:
  - `frontend/src/components/CommandPalette.tsx`
  - `frontend/src/components/ShortcutsOverlay.tsx`
  - wired in `frontend/src/App.tsx`

### Role-based Onboarding Delivered

- Added role-specific onboarding step model:
  - `frontend/src/lib/onboardingModel.ts`
  - `frontend/src/lib/onboardingModel.test.ts`
- Added onboarding overlay UI with skip/replay:
  - `frontend/src/components/OnboardingOverlay.tsx`
- Integrated onboarding persistence per `(peerId, role)` via localStorage:
  - `frontend/src/App.tsx`
- Added onboarding styling:
  - `frontend/src/styles.css`

### Fog Workflow Persistence Delivered

- Added backend persistent re-hide path:
  - command contract: `api_contracts/commands.py` (`HideCellCommand`)
  - request schema: `api/schemas.py` (`HideCellRequest`)
  - map/engine support: `engine/map_state.py`, `engine/game_state.py`
  - service mutation: `app/services/session_service.py` (`hide_cell`)
  - dispatcher wiring: `app/commands/dispatcher.py` (`hide_cell`)
  - API endpoint: `POST /api/sessions/{session_id}/hide-cell` in `api/http_api.py`
- Frontend wired `re-hide` mode to persistent backend call:
  - `frontend/src/lib/apiClient.ts` (`hideCell`)
  - `frontend/src/App.tsx`
  - `frontend/src/components/MapCanvas.tsx`
- Added API regression assertion:
  - `tests/test_signaling_service.py` now verifies `hide-cell` returns `200`.

### Realtime Session-Switch Polish Delivered

- Hardened websocket reconnect behavior in `frontend/src/realtime/sessionRealtime.ts`:
  - websocket URL/auth context now rebuilt per reconnect attempt (prevents stale token/session URL reuse),
  - connection nonce guard prevents stale websocket callbacks from racing new connections,
  - auth close (`1008`) applies stronger backoff to reduce noisy reconnect churn,
  - clearer status when waiting for valid auth context.

### Phase 1 Task 1 Foundation In Progress (Worktree)

- Worktree branch: `feature/phase1-heartbeat`
- Location: `.worktrees/phase1-heartbeat`
- Completed there so far:
  - added `app/session_store_config.py` with default Phase 1 feature flags:
    - `chat_visible_to_players`
    - `whispers_show_contents_to_non_participants`
    - `dice_breakdown_visible_to_players`
    - `presence_visible_to_players`
    - `pings_visible_to_players`
  - updated `app/services/session_service.py` to:
    - initialize `feature_flags` on session creation,
    - backfill defaults in `_ensure_metadata`,
    - provide `get_feature_flags(session_id)` and `update_feature_flags(session_id, updates)`.
  - added/updated tests:
    - `tests/test_session_store_config.py`
    - `tests/test_session_store.py`
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_session_store_config.py tests/test_session_store.py -q` passed.

### Phase 1 Task 2 Chat Backend Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - added chat mutation permission in `app/policies/permission_matrix.py`
  - added minimal chat contracts and request wiring:
    - `api_contracts/events.py`
    - `api_contracts/commands.py`
    - `api/schemas.py`
  - extended `app/commands/dispatcher.py` with `send_chat_message`
  - added `SessionService.send_chat_message(...)` in `app/services/session_service.py`
  - added HTTP endpoint `POST /api/sessions/{session_id}/chat/send` in `api/http_api.py`
  - chat messages currently:
    - require command identity,
    - increment revision,
    - append to in-session `chat_log`,
    - publish `chat_message_sent` events for replay.
  - added/updated tests:
    - `tests/test_command_dispatcher.py`
    - `tests/test_signaling_service.py`
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_command_dispatcher.py tests/test_signaling_service.py -q` passed.

### Phase 1 Task 3 Dice Backend Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - added minimal safe dice engine in `engine/dice.py`
    - currently supports basic `NdM+K` / `NdM-K` formulas
    - returns `formula`, `rolls`, `modifiers`, `total`, and `breakdown`
  - added roll request/command wiring:
    - `api_contracts/commands.py`
    - `api/schemas.py`
  - extended `app/commands/dispatcher.py` with `roll_dice`
  - added `SessionService.roll_dice(...)` in `app/services/session_service.py`
  - added HTTP endpoint `POST /api/sessions/{session_id}/roll` in `api/http_api.py`
  - rolls currently:
    - require command identity,
    - increment revision,
    - append a roll entry into in-session `chat_log`,
    - publish `dice_rolled` events for replay.
  - added/updated tests:
    - `tests/test_dice_engine.py`
    - `tests/test_command_dispatcher.py`
    - `tests/test_signaling_service.py`
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_dice_engine.py tests/test_command_dispatcher.py tests/test_signaling_service.py -q` passed.

### Phase 1 Task 4 Ping Backend Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - added ping request/command wiring:
    - `api_contracts/commands.py`
    - `api/schemas.py`
  - extended `app/commands/dispatcher.py` with `create_ping`
  - added `SessionService.create_ping(...)` in `app/services/session_service.py`
  - added HTTP endpoint `POST /api/sessions/{session_id}/ping` in `api/http_api.py`
  - pings currently:
    - require command identity,
    - increment revision,
    - append ping entries to in-session `pings`,
    - publish `map_ping_created` events for replay.
  - added/updated tests:
    - `tests/test_command_dispatcher.py`
    - `tests/test_signaling_service.py`
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_command_dispatcher.py tests/test_signaling_service.py -q` passed.

### Phase 1 Task 5 Event Visibility Filtering Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - extended `SessionService.filter_event_for_view(...)` for new Phase 1 event types:
    - `chat_message_sent`:
      - hides GM-only messages from non-GM viewers,
      - hides whisper payloads from non-participants unless `whispers_show_contents_to_non_participants` is enabled.
    - `dice_rolled`:
      - redacts `rolls`, `modifiers`, and `breakdown` for non-GM viewers when `dice_breakdown_visible_to_players` is disabled.
    - `map_ping_created`:
      - hides ping events from non-GM viewers when `pings_visible_to_players` is disabled.
  - added tests in `tests/test_signaling_service.py` to lock these behaviors:
    - GM-only chat hidden from player replay
    - roll breakdown redacted for players when flag disabled
    - ping hidden from players when flag disabled
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_signaling_service.py -q` passed.

### Phase 1 Task 6 Frontend API + Realtime Wiring Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - extended frontend API client in `frontend/src/lib/apiClient.ts`:
    - `sendChatMessage(...)`
    - `sendRoll(...)`
    - `sendPing(...)`
  - extended realtime handler in `frontend/src/realtime/sessionRealtime.ts`:
    - new optional callback `onTableEvent(eventType, payload)`
    - callback now fires for Phase 1 event types:
      - `chat_message_sent`
      - `dice_rolled`
      - `map_ping_created`
  - added targeted frontend test file:
    - `frontend/src/lib/realtimePhase1.test.ts`
    - verifies API methods hit expected endpoints and realtime callback receives Phase 1 event payloads.
- Verification already run in the worktree:
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test -- src/lib/realtimePhase1.test.ts` passed.

### Phase 1 Task 7 ChatPanel UI Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - added new component:
    - `frontend/src/components/ChatPanel.tsx`
      - renders chat/system/roll lines
      - supports input submit
      - parses `/roll ...` to call roll endpoint
      - sends normal text to chat endpoint
  - integrated chat into app shell:
    - `frontend/src/App.tsx`
      - imports/renders `ChatPanel` in side stack
      - maintains `chatMessages` state
      - appends chat/roll/ping entries from realtime `onTableEvent`
  - added chat styling:
    - `frontend/src/styles.css`
  - added tests:
    - `frontend/src/components/ChatPanel.test.tsx`
      - verifies rendering of messages
      - verifies `/roll` submit dispatches roll API call.
- Verification already run in the worktree:
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test -- src/components/ChatPanel.test.tsx src/lib/realtimePhase1.test.ts` passed.

### Phase 1 Task 8 Presence Roster UI Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - added presence roster component:
    - `frontend/src/components/PresenceRoster.tsx`
    - renders peer list with role chips
    - supports visibility gating (`canSeePresence`)
  - integrated into app:
    - `frontend/src/App.tsx`
    - roster now renders in side stack
    - visibility rule:
      - GM/AssistantGM always see roster
      - players/observers follow `session.feature_flags.presence_visible_to_players` (default true)
  - extended session type:
    - `frontend/src/types.ts`
    - added optional `feature_flags` shape for Phase 1 flags
  - added tests:
    - `frontend/src/components/PresenceRoster.test.tsx`
- Verification already run in the worktree:
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test -- src/components/PresenceRoster.test.tsx src/components/ChatPanel.test.tsx src/lib/realtimePhase1.test.ts` passed.

### Phase 1 Task 9 Map Ping UX Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - extended `frontend/src/components/MapCanvas.tsx`:
    - new props:
      - `onPing(x, y)`
      - `pingMarkers`
    - Ctrl/Cmd-click on map now emits ping via `onPing`
    - renders transient ping circles/labels from `pingMarkers`
  - updated `frontend/src/App.tsx`:
    - imports/uses `sendPing(...)`
    - added `pingMarkers` state
    - on realtime `map_ping_created` event:
      - appends marker
      - auto-removes marker after `duration_ms` (default 2000ms)
    - passes `onPing` + `pingMarkers` into `MapCanvas`
  - added tests:
    - `frontend/src/components/MapCanvas.test.tsx`
      - verifies ctrl-click emits ping callback
      - verifies ping label renders from marker data.
- Verification already run in the worktree:
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test -- src/components/MapCanvas.test.tsx src/components/PresenceRoster.test.tsx src/components/ChatPanel.test.tsx src/lib/realtimePhase1.test.ts` passed.

### Phase 1 Task 10 GM Feature-Flag Management Slice In Progress (Worktree)

- Still on worktree branch: `feature/phase1-heartbeat`
- Completed there so far:
  - backend feature-flag management endpoint:
    - `POST /api/sessions/{session_id}/feature-flags` in `api/http_api.py`
    - request schema in `api/schemas.py` (`UpdateFeatureFlagsRequest`)
    - endpoint requires command identity and GM/AssistantGM authorization
    - writes through `SessionService.update_feature_flags(...)`
  - backend tests extended in `tests/test_signaling_service.py`:
    - non-GM cannot update flags (`403`)
    - GM can update flags (`200`) and receives updated values.
  - frontend API client extension:
    - `updateSessionFeatureFlags(...)` in `frontend/src/lib/apiClient.ts`
  - frontend GM controls:
    - new `frontend/src/components/FeatureFlagsPanel.tsx`
    - integrated in `frontend/src/App.tsx`
    - supports toggling:
      - presence visibility to players
      - dice breakdown visibility to players
    - updates local session feature flag state from backend response
  - frontend tests:
    - `frontend/src/components/FeatureFlagsPanel.test.tsx`
- Verification already run in the worktree:
  - `python3 -m pytest tests/test_signaling_service.py -q` passed
  - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test -- src/components/FeatureFlagsPanel.test.tsx src/components/PresenceRoster.test.tsx src/components/MapCanvas.test.tsx src/components/ChatPanel.test.tsx src/lib/realtimePhase1.test.ts` passed.

## Verification Run During Recent Sessions

- `python3 -m pytest -q` passed.
- `python3 -m pytest -q tests/test_signaling_service.py` passed.
- `npm --prefix frontend run test` passed (includes `uxPolicy`, `combatUtils`, onboarding model, and panel tests).
- `npm --prefix frontend run build` passed.
- Desktop smoke checks repeatedly reached readiness:
  - frontend on `127.0.0.1:5173`,
  - backend on `127.0.0.1:8000`,
  - `/health/ready` returned `200`.

## Key Files Touched Recently

- `desktop-electron/main.js`
- `desktop-electron/preload.js`
- `desktop-electron/package.json`
- `scripts/run_desktop.sh`
- `frontend/src/lib/desktopBridge.ts`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/components/layout/AppShell.tsx`
- `frontend/src/components/layout/RightDrawer.tsx`
- `frontend/src/components/layout/BottomTray.tsx`
- `frontend/src/components/StatusRail.tsx`
- `frontend/src/components/CommandPalette.tsx`
- `frontend/src/components/ShortcutsOverlay.tsx`
- `frontend/src/components/OnboardingOverlay.tsx`
- `frontend/src/components/MapCanvas.tsx`
- `frontend/src/realtime/sessionRealtime.ts`
- `frontend/src/components/InitiativePanel.tsx`
- `frontend/src/lib/uxPolicy.ts`
- `frontend/src/lib/uxTelemetry.ts`
- `frontend/src/lib/combatUtils.ts`
- `frontend/src/lib/onboardingModel.ts`
- `frontend/src/lib/apiClient.ts`
- `frontend/src/lib/uxPolicy.test.ts`
- `frontend/src/lib/combatUtils.test.ts`
- `frontend/src/lib/onboardingModel.test.ts`
- `docs/ux/information-architecture.md`
- `docs/ux/interaction-model.md`
- `docs/ux/onboarding-flows.md`
- `docs/ux/phase-plan.md`
- `docs/ux/wireframes.md`
- `docs/ux/implementation-tickets.md`
- `api/http_api.py`
- `api/schemas.py`
- `api_contracts/commands.py`
- `app/commands/dispatcher.py`
- `app/services/session_service.py`
- `engine/map_state.py`
- `engine/game_state.py`
- `tests/test_signaling_service.py`

## Remaining Work (Highest Priority)

1. **Final UX finish pass (small)**
   - Add a few more context-aware command palette actions and shortcut hints.
   - Optional onboarding completion telemetry/analytics polish.
2. **Map/canvas theme parity**
   - Tokenize remaining inline map colors for full grimdark consistency.
3. **Desktop quality**
   - Keep devtools closed for normal runs.
   - Add dedicated smoke script that starts/stops cleanly and checks readiness endpoints.
4. **Phase 2 – Multi-scene + campaign management (next major phase)**
   - Use roadmap: `/Users/jkoch/.cursor/plans/premium_vtt_polish_roadmap_8e3cc69a.plan.md` (Phase 2 section).
   - Preserve completed Phase 1 behavior in `feature/phase1-heartbeat`.
   - Start with scene data model + migration strategy, then scene list/create/activate APIs, then GM preview vs push-to-players UI.
   - Maintain backend-authoritative mutations, revision/idempotency semantics, and replay/event filtering guarantees.

## Suggested Prompt For Next Agent

> Continue from `SESSION_HANDOFF.md` and do not redo completed Phase 1 work in `.worktrees/phase1-heartbeat` (branch `feature/phase1-heartbeat`). Treat Phase 1 table-heartbeat features as implemented and verified. Start Phase 2 from `/Users/jkoch/.cursor/plans/premium_vtt_polish_roadmap_8e3cc69a.plan.md`:
> 1) Introduce scenes as first-class data (session/campaign model + migrations),
> 2) Add scene list/create/activate backend APIs with permissions and replay/event behavior,
> 3) Implement GM preview vs push-to-players scene controls in frontend.
> Preserve backend-authoritative command flow, revision/idempotency, and event filtering guarantees. Verify each logical slice with targeted tests, then run full verification:
> - `python3 -m pytest -q`
> - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test`
> - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" run build`

## Phase 2 Task 1 Kickoff Checklist (for next agent)

1. **Branch/worktree continuity**
   - Continue in `.worktrees/phase1-heartbeat` on `feature/phase1-heartbeat`.
   - Confirm baseline still passes before edits:
     - `python3 -m pytest -q`
     - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test`

2. **Define scene data model (backend-first)**
   - Extend session/campaign storage in `app/services/session_service.py` to include:
     - scene list (id, name, map metadata, per-scene settings),
     - `active_scene_id`,
     - optional `preview_scene_id` (GM-only).
   - Keep data backward-compatible with existing sessions (defaults on load/create).

3. **Schema/migration pass**
   - Increment schema version and wire migration path in:
     - `app/migrations/runner.py`
     - `app/migrations/status.py`
   - Add/extend migration tests in `tests/test_migration_runner.py`.

4. **Scene API contracts and endpoints**
   - Add request/command contracts in:
     - `api/schemas.py`
     - `api_contracts/commands.py`
     - `app/commands/dispatcher.py`
   - Add endpoints in `api/http_api.py`:
     - `GET /api/campaigns/{id}/scenes`
     - `POST /api/campaigns/{id}/scenes`
     - `POST /api/sessions/{id}/scenes/{scene_id}/activate`
   - Enforce GM/AssistantGM permissions for create/activate.

5. **Replay/event behavior**
   - Emit scene lifecycle events (created/activated) with revision support.
   - Ensure replay and `filter_event_for_view` behavior remains correct and role-safe.

6. **Minimum frontend integration for Task 1**
   - Add API client methods for scene list/create/activate in `frontend/src/lib/apiClient.ts`.
   - Stub scene list controls in existing app shell (`frontend/src/App.tsx`) for GM use only.
   - Player view should follow active scene only.

7. **Verification before handoff**
   - Run targeted tests for scenes/migrations + existing signaling tests.
   - Run full verification:
     - `python3 -m pytest -q`
     - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" test`
     - `npm --prefix "/Users/jkoch/DND/.worktrees/phase1-heartbeat/frontend" run build`

