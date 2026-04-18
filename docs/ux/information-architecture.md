# Information Architecture

## Product goals
- Keep the map as the primary surface at all times.
- Default to a simpler player view; progressively reveal GM and Host/Admin controls.
- Ensure realtime state is continuously legible in a persistent status rail.

## Runtime role model
- `Player`: baseline play role, minimal surface, no admin/ops controls.
- `GM`: gameplay authority role with encounter, map, and permission management.
- `Host/Admin`: capability superset layered on top of `GM`; adds ops/debug/recovery and elevated configuration, not a separate parallel gameplay role.

## App shell contract
- `AppShell` owns visual composition, responsive mode switching, and local open/close UI state.
- `AppShell` exposes named slots and emits UI events upward.
- `App.tsx` remains orchestration owner (session/auth/realtime/data mutation/permission derivation).
- Shell components stay presentational and stateless except local expand/collapse and focus-affordance display state.

## Shell regions
- Center: map canvas and token interactions.
- Left rail: primary mode/tool selection only.
- Right drawer: contextual inspector and object/session details.
- Bottom tray: chat/combat workspace; one major tab expanded at a time.
- Top bar: session identity, role badge, invite/share, command entry trigger, and connection summary.
- Status rail: persistent, always-visible state indicators.

## Expansion and compact rules
- One major side drawer section expanded at a time.
- One major bottom tray tab expanded at a time.
- Allowed compact exceptions:
  - Bottom tray compact strip remains visible for awareness.
  - Right drawer compact summary remains visible for context.
- Compact summary minimums:
  - Chat: unread count.
  - Combat: active combatant/current turn.
  - Selection: selected token name + context badge.

## Role policy matrix
| Surface | Player | GM | Host/Admin |
|---|---|---|---|
| Left rail core tools | Visible | Visible | Visible |
| Advanced map/fog controls | Hidden by default | Visible in tool popover | Visible in tool popover |
| Token contextual quick actions | Limited | Full gameplay set | Full gameplay set |
| Right drawer entity inspection | Visible | Visible | Visible |
| Permission management | Hidden | Visible | Visible |
| Backup/import/migration/ops controls | Hidden | Hidden by default | Visible via Admin route |
| Recovery/debug entry points on failures | Read-only status + retry | Retry + diagnostics | Retry + diagnostics + admin actions |

## Responsive layout modes
- `wideDesktop` (`>= 1360px`)
  - Left rail + map + right drawer + bottom tray affordances visible together.
  - Expanded drawer/tray behavior fully available.
- `narrowDesktop` (`1024px - 1359px`)
  - Compact summaries default on right drawer and bottom tray.
  - One major expanded panel at a time; map remains dominant.
- `minSupportedWidth` (`900px - 1023px`)
  - No overlap breakage.
  - Critical controls (map tools, status, session actions) remain reachable.
- `< 900px`
  - Out of scope for this desktop-first slice.
  - Show constrained-layout warning if entered.

## Failure and recovery routing
- Hide advanced controls during normal play.
- On failures (`backend unavailable`, `permission denied`, reconnect loops), expose explicit recovery route:
  - Retry action in-context.
  - Diagnostic status details.
  - Admin/settings link for Host/Admin users.
