# Phase 1 – Chat, Dice, Presence, Pings (Capability-Sliced) – Design

> **Goal:** Add table-heartbeat features (chat log, dice/roll pipeline, presence roster, and map pings) with authoritative backend, WS/replay, and configurable visibility, following existing command/revision/permission patterns.

## 1. Scope and Non-Goals

### In Scope

- **Chat log**
  - Plain text chat messages.
  - System messages (join/leave, later roll summaries).
  - GM-only messages.
  - Whispers between peers.
  - Inclusion in WS stream and replay.
- **Dice / roll pipeline**
  - Minimal, safe dice engine in Python:
    - `NdM`, `NdM+K`, `NdM-K`.
    - Advantage/disadvantage helpers (e.g. `adv 1d20+5`, `dis 1d20+3` or similar minimal shape).
  - Canonical `RollResult` structure (formula, rolls, modifiers, total, breakdown).
  - `/roll` endpoint, WS events, and unified roll pipeline usable by future macros.
- **Presence roster**
  - Lightweight roster based on existing `session.peers`, `peer_roles` and realtime signals.
  - Always-on for GMs; visibility to players controlled by feature flags.
- **Map pings**
  - GM or players can ping a position on the active map.
  - Transient visual markers on all appropriate clients.

### Out of Scope (for this phase)

- Long-term chat persistence outside session snapshots (e.g. campaign-wide chat history).
- Rich text/markdown/emote packs.
- Arbitrary macro management UI.
- Non-d20 dice expressions beyond simple `NdM(+/-K)` and adv/dis.
- Audio/ambience, scenes/campaigns, 5e-aware sheets, modules (other roadmap phases).

## 2. Security, Config, and Visibility Model

### Global Config

- Introduce a **server-side config** module or extend existing config to define Phase 1 defaults:
  - `CHAT_ENABLED = True`
  - `DICE_ENABLED = True`
  - `PINGS_ENABLED = True`
  - `PRESENCE_ENABLED = True`
  - Default visibility:
    - Chat visible to players, including player-to-player messages.
    - Whispers enabled with full contents visible to intended recipients only.
    - GM-only messages hidden from non-GM peers.
    - Dice totals visible to all; breakdown visible by default.
    - Presence roster visible to players by default.
    - Pings visible to all clients by default.
- Config should be **pure Python / static data** (no env reads at call sites) so it can be imported where needed and unit-tested.

### Per-Session Overrides

- Extend session state (managed by `SessionService`) with a `feature_flags` or `visibility` structure, e.g.:

  ```python
  {
      "chat_visible_to_players": True,
      "whispers_show_contents_to_non_participants": False,
      "dice_breakdown_visible_to_players": True,
      "presence_visible_to_players": True,
      "pings_visible_to_players": True,
  }
  ```

- The **effective value** for a flag is derived by:
  - Starting from global config default.
  - Overriding with any stored per-session flag (if present).
- GMs have **full control**:
  - There are no hard ceilings; GMs may choose to expose GM-only and whisper content fully, or hide more than defaults.
  - However, the UI should make “safe” defaults obvious and avoid surprising exposure.

### Enforcement

- All visibility decisions are enforced in the **backend**:
  - When emitting events to the WS stream, events carry **raw payload + visibility metadata** (e.g. `gm_only`, `whisper_targets`, `visibility_flags`).
  - `SessionService.filter_event_for_view` applies feature flags, roles, and peer identity to decide:
    - Whether the viewer can see the event at all.
    - Whether to show full payload vs. a redacted/summary form.
  - Replay uses the same filter path so viewing history and live events are consistent.
- The frontend never relies on client-side filtering for secrecy; it merely renders what the backend already filtered.

## 3. Data Contracts and Events

### New Event DTOs

- Extend `api_contracts/events.py` with event DTOs such as:
  - `ChatMessageEvent`:
    - `id`, `session_id`, `author_peer_id`, `author_role`, `targets` (optional list of peer ids for whispers), `gm_only: bool`, `kind: Literal["plain", "system", "roll"]`, `text`, `created_at`.
  - `RollResultEvent`:
    - `id`, `session_id`, `author_peer_id`, `context` (e.g. actor/token id), `result: RollResult`, `gm_only: bool`, `targets` (for secret rolls), `created_at`.
  - `MapPingEvent`:
    - `id`, `session_id`, `author_peer_id`, `x`, `y`, `label` (optional), `duration_ms` (optional), `created_at`.

- Each event DTO must integrate with existing event types and be included in any union of session events used by HTTP/WS layers.

### Request Schemas

- Extend `api/schemas.py` with request models:
  - `SendChatMessageRequest`:
    - `text: str`, `targets: Optional[List[str]]`, `gm_only: bool = False`, potential `kind` field for future extensibility.
  - `RollRequest`:
    - `formula: str`, `context_actor_id: Optional[str]`, `context_token_id: Optional[str]`, `advantage: Optional[bool]`, `disadvantage: Optional[bool]`.
  - `PingRequest`:
    - `x: float`, `y: float`, `label: Optional[str]`, `duration_ms: Optional[int]`.

### Dice Engine Types

- Define a canonical `RollResult` type (likely in a shared module under `engine/` or `app/services/`) with fields:

  ```python
  class RollResult(BaseModel):
      formula: str
      rolls: List[int]
      modifiers: List[int]
      total: int
      breakdown: str  # human-readable summary, e.g. "1d20 (17) + 5"
      advantage: Optional[bool]
      disadvantage: Optional[bool]
  ```

- Future macros, 5e sheets, and any other roll producers must call into the **same engine** to generate `RollResult`.

## 4. Backend Behavior (SessionService, Commands, Endpoints)

### Endpoints

- Add the following HTTP endpoints in `api/http_api.py`:
  - `POST /api/sessions/{session_id}/chat/send` → send a chat message.
  - `POST /api/sessions/{session_id}/roll` → perform a roll using the dice engine.
  - `POST /api/sessions/{session_id}/ping` → create a map ping in the active scene/map.
- Each endpoint:
  - Authenticates the caller and maps them to a session and peer id.
  - Validates the request with new Pydantic schemas.
  - Translates into corresponding **command/dispatcher calls** so that authoritative logic lives in `SessionService`.

### Commands and Dispatcher

- Extend `api_contracts/commands.py` and `app/commands/dispatcher.py` with commands:
  - `SendChatMessageCommand`
  - `RollDiceCommand`
  - `CreatePingCommand`
- Dispatcher:
  - Validates the session/peer/role context.
  - Calls into new `SessionService` methods:
    - `SessionService.send_chat_message(...)`
    - `SessionService.roll_dice(...)`
    - `SessionService.create_ping(...)`

### SessionService Logic

- **Chat log**
  - Maintain an in-memory list per session of chat/roll entries (a minimal structure that mirrors event payloads).
  - Optionally attach this to session snapshot for “resume session” flows later; not required in this phase.
  - When a new chat/roll arrives:
    - Normalize into a consistent structure and append to the in-memory log.
    - Emit a `ChatMessageEvent` or `RollResultEvent`.
    - Record event in the event log for replay.
- **Dice engine integration**
  - Implement a pure function or small helper class that:
    - Parses input formulas constrained to our supported grammar.
    - Produces a `RollResult`.
    - Does **not** allow arbitrary Python eval or unbounded string operations.
  - `SessionService.roll_dice`:
    - Uses the engine to compute a `RollResult`.
    - Creates a `RollResultEvent` with appropriate visibility metadata (GM-only, whisper targets).
    - Optionally also posts a system chat line referencing the roll.
- **Map pings**
  - `SessionService.create_ping`:
    - Validates that the session has an active map/scene.
    - Normalizes coordinates into the map’s coordinate system.
    - Emits `MapPingEvent` with a short lifetime; no persistent storage beyond replay is required.

### Filtering and Redaction

- Extend `SessionService.filter_event_for_view` (and any related helpers) to handle new event types:
  - **Chat / Roll events**:
    - If `gm_only` and viewer is not a GM (or higher privilege), respect feature flags:
      - If the session flag says “hide GM-only events entirely” → viewer receives no event.
      - If “show GM-only events as summaries” → viewer sees a system line like “GM made a private roll.”
    - If `targets` is non-empty (whispers):
      - If viewer is sender or in `targets` → show full message/roll.
      - Else:
        - Hide entirely, or show a generic “private message sent” based on feature flags.
    - Dice breakdown:
      - If `dice_breakdown_visible_to_players` is False and viewer is not GM → only expose `total` and a generic breakdown string.
  - **Map pings**:
    - If `pings_visible_to_players` is False and viewer is not GM → either hide pings entirely or restrict to GM-only based on per-session flag.
- Ensure **replay** calls the same filter path so historical views obey the same rules.

## 5. Frontend Behavior and Components

### Chat Panel

- Add `ChatPanel.tsx` under `frontend/src/components/`:
  - Displays a scrollable list of messages:
    - Plain chat lines.
    - System messages (including join/leave and roll summaries).
    - Styled roll outputs displaying `RollResult` (total, breakdown, metadata).
  - Input area:
    - Sends plain text messages via `/chat/send`.
    - Detects `/roll 1d20+5` or bare `1d20+5`:
      - If prefixed with `/roll`, treat as explicit roll.
      - If bare formula, either:
        - Assume roll intent; or
        - Require `/roll` prefix (final choice can be UX-tuned, but parsing should be isolated so policy is adjustable).
    - Allows GM to mark message as GM-only and choose whisper targets when applicable.
- Integration:
  - Wire into `BottomTray` as a tab, with state managed by `App` (or an appropriate container).
  - Subscribe to new WS events via `sessionRealtime` and append messages in the panel’s local state/store.

### Presence Roster

- Add a small presence roster UI (likely in `StatusRail` or `RightDrawer`):
  - Renders `session.peers` with role badges from existing role model.
  - Indicates online/connected/disconnected based on realtime status from `sessionRealtime`.
  - Honors visibility flags:
    - If players cannot see presence, hide or show a reduced view to them while GMs see the full roster.

### Map Pings

- Extend `MapCanvas.tsx`:
  - Handle Ctrl+click (or similar modifier) to emit a ping:
    - Coordinate conversion from screen to map coordinate space (reuse existing helper logic if present).
    - POST to `/ping` endpoint via `apiClient`.
  - Subscribe to `MapPingEvent` via realtime layer:
    - Render a transient marker at the given coordinates with a small animation and lifetime.
    - Remove markers after `duration_ms` or a default timeout.

### GM Feature Controls UI

- Add or extend a GM-only settings surface (could be in a tray/drawer panel):
  - Surface toggles for:
    - “Players can see chat messages.”
    - “Players can see other players’ whispers contents.”
    - “Players can see dice roll breakdowns.”
    - “Players can see presence roster.”
    - “Players can see map pings.”
  - Calls a GM-only config endpoint to update per-session overrides in the backend.
  - Shows current state derived from effective session config.

## 6. Realtime and Replay Integration

- Reuse existing websocket/session realtime infrastructure:
  - Register handlers for `ChatMessageEvent`, `RollResultEvent`, `MapPingEvent` in `sessionRealtime`.
  - Fan them out to:
    - `ChatPanel` for chat/roll events.
    - Map canvas ping layer for ping events.
    - Presence roster for any presence updates if new events are introduced.
- Replay:
  - When a client attaches to a session with history, ensure:
    - Chat and roll events in the event log are filtered and replayed correctly into the chat UI.
    - Ping events may or may not be replayed (for now, we can treat pings as **ephemeral for live play only** and skip replaying them, or show only recent ones; decision can be encoded in SessionService).

## 7. Testing Strategy

### Backend

- Add tests that:
  - Verify `/chat/send`:
    - Emits an event and is visible to appropriate peers.
    - Enforces GM-only and whispers visibility with different feature flag settings.
  - Verify `/roll`:
    - Produces a deterministic `RollResult` for simple formulas.
    - Honors advantage/disadvantage flags.
    - Enforces visibility rules on totals vs breakdowns.
  - Verify `/ping`:
    - Emits `MapPingEvent` to all or GM-only based on feature flags.
  - Verify `filter_event_for_view` behavior for all new event shapes.

### Frontend

- Vitest/RTL tests:
  - Chat parsing:
    - `/roll` commands and bare formulas are parsed correctly.
    - Messages render as expected in `ChatPanel` given a stream of synthetic events.
  - Visibility:
    - Given mocked feature flag states and roles, verify that messages, rolls, presence, and pings render or hide correctly.
  - Pings rendering:
    - `MapCanvas` renders markers in response to ping events and clears them after timeout.

## 8. Execution Order (Capability-Sliced)

1. Implement **backend chat + events + visibility** (without UI), including tests.
2. Implement **frontend ChatPanel + realtime wiring** and tests.
3. Implement **backend dice engine + /roll + RollResultEvent + redaction**, with tests.
4. Implement **frontend dice UX in ChatPanel**, with tests.
5. Implement **backend ping endpoint + events**, with tests.
6. Implement **frontend pings in MapCanvas**, with tests.
7. Implement **presence roster UI** (mostly frontend, relying on existing state).
8. Implement **GM feature flag endpoints + UI**, with tests.

