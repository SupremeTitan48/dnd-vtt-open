# Interaction Model

## Core principles
- Map-first operation: every major action should preserve spatial context.
- Progressive disclosure: show advanced controls only when role and context require them.
- Interaction continuity: selection and focus persist when drawers/trays open or collapse.

## Primary interactions
- Single click token: select token.
- Shift/Cmd click token: multi-select token.
- Drag token: move selected controlled token(s).
- Double-click token: open deeper details in right drawer.
- Right-click token: open contextual actions.

## Contextual quick actions
- Baseline actions near selected token:
  - Open sheet/inspector.
  - Adjust HP (damage/heal).
  - Add condition.
  - Add to initiative.
  - Ping/focus map.
  - More actions entry.
- Player quick-action set is smaller than GM/HostAdmin.
- GM/HostAdmin receives expanded contextual operations in "More".

## Drawer and tray behavior
- Right drawer and bottom tray support `expanded` and `compact` states.
- Only one major drawer section and one major tray tab can be fully expanded.
- Compact states remain informative:
  - Drawer summary: selected token/entity summary.
  - Tray summary: unread chat + active turn.
- Collapse/expand must not clear selection, active token, or active combat focus.

## Combat-map integration
- Combat lives in docked bottom tray.
- Selecting a combatant centers/highlights associated map token.
- Adding initiative should be available directly from token context interactions.

## Command and shortcut model (phase scaffold)
- Command palette trigger: `Ctrl/Cmd+K`.
- Shortcut discoverability shown in tooltips/menus.
- Keyboard/mouse baseline:
  - Double-click: details.
  - Right-click: context menu.
  - Arrow keys: token nudging (existing behavior preserved).
  - Additional phase tickets define measure/fog/tray toggles.

## Status rail model
- Persistent rail displays active app/session state.
- State precedence:
  - `backend unavailable` > `permission denied` > `reconnecting` > `syncing` > `replay available` > `saved` > `connected`.
- Simultaneous-state rule:
  - Highest-severity state is primary.
  - Secondary non-conflicting states may appear as subordinate chips.
- Persistence:
  - `permission denied` persists until dismissal or clear condition.
  - Positive states (`saved`, `connected`) are non-sticky if superseded.

## Accessibility and interaction safety
- Role-gated controls must be blocked in rendering and handlers.
- Player cannot trigger Host/Admin actions through hidden controls, keyboard focus, or command execution path.
