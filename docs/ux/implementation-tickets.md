# Implementation Tickets (Phase 1)

## UX-001: Create shell layout components
- Files:
  - `frontend/src/components/layout/AppShell.tsx`
  - `frontend/src/components/layout/RightDrawer.tsx`
  - `frontend/src/components/layout/BottomTray.tsx`
- Scope:
  - Implement slot-based shell contract.
  - Keep shell presentational except local expand/collapse state.
  - Add compact summary surfaces.
- Acceptance:
  - `App.tsx` orchestrates data/actions.
  - Drawer/tray support compact + expanded states.

## UX-002: Add status rail with precedence model
- Files:
  - `frontend/src/components/StatusRail.tsx`
  - `frontend/src/App.tsx`
- Scope:
  - Structured status states, precedence, persistence behavior.
  - Backend/realtime/action status merged into one rail.
- Acceptance:
  - Highest-severity state displayed as primary.
  - `permission denied` can persist until dismissed/cleared.

## UX-003: Role policy matrix in code
- Files:
  - `frontend/src/lib/rolePolicy.ts` (new)
  - `frontend/src/App.tsx`
- Scope:
  - Encode Player/GM/HostAdmin visibility and action gating.
  - Host/Admin modeled as capability superset of GM.
- Acceptance:
  - Player cannot access Host/Admin actions through hidden UI, focus, or handlers.

## UX-004: Compact summary and interaction continuity
- Files:
  - `frontend/src/components/layout/RightDrawer.tsx`
  - `frontend/src/components/layout/BottomTray.tsx`
  - `frontend/src/App.tsx`
- Scope:
  - Preserve selection/focus across collapse/expand.
  - Ensure compact summary minimums are shown.
- Acceptance:
  - Selected token context remains intact after panel toggles.

## UX-005: Lightweight telemetry events
- Files:
  - `frontend/src/lib/uxTelemetry.ts` (new)
  - `frontend/src/components/layout/AppShell.tsx`
  - `frontend/src/components/layout/RightDrawer.tsx`
  - `frontend/src/components/layout/BottomTray.tsx`
  - `frontend/src/components/StatusRail.tsx`
- Scope:
  - Emit event names:
    - `drawer_opened`
    - `drawer_collapsed`
    - `tray_opened`
    - `tray_collapsed`
    - `tray_tab_switched`
    - `status_visible`
    - `status_priority_resolved`
    - `selection_persisted_after_collapse`
    - `role_policy_blocked_action`
  - Include payload baseline: `role`, `panelOrTabId`, `viewportMode`, `sessionIdHash`, `timestamp`.
  - `sessionIdHash = sha256(telemetrySalt + ":" + sessionId)` truncated to 12 chars.
- Acceptance:
  - Events emitted in development logs without exposing raw session IDs.

## UX-006: Responsive mode implementation
- Files:
  - `frontend/src/styles.css`
  - `frontend/src/components/layout/AppShell.tsx`
- Scope:
  - Implement layout behavior for:
    - `wideDesktop >= 1360px`
    - `narrowDesktop 1024-1359px`
    - `minSupportedWidth 900-1023px`
  - Constrained-layout warning for `< 900px`.
- Acceptance:
  - No overlap breakage in supported range.
  - Critical controls and status remain reachable.
