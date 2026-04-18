# Wireframes

## Wide desktop shell (`>= 1360px`)

```text
+--------------------------------------------------------------------------------------+
| TopBar: Session | Role | Invite | CmdK | Connection summary                          |
+----------------------+-------------------------------------------+--------------------+
| LeftRail             |                Map Canvas                 | RightDrawer        |
| - Select/Move        |                                           | (expanded section) |
| - Measure            |             Tokens + Fog + Tools          | or compact summary |
| - Fog (GM+)          |                                           |                    |
+----------------------+-------------------------------------------+--------------------+
| BottomTray compact summary: [Chat unread] [Combat current turn] [Selection summary] |
| BottomTray expanded tab (one at a time): Chat OR Combat                                 |
+--------------------------------------------------------------------------------------+
| StatusRail: primary state + secondary state chips + retry/recovery links             |
+--------------------------------------------------------------------------------------+
```

## Narrow desktop shell (`1024px - 1359px`)

```text
+--------------------------------------------------------------------------------------+
| TopBar (compressed): Session | Role | Invite | CmdK | Connection                     |
+----------------------+-------------------------------------------+--------------------+
| LeftRail compact     |                Map Canvas                 | RightDrawer compact|
| primary tools only   |                                           | summary first      |
+----------------------+-------------------------------------------+--------------------+
| BottomTray compact-first: [Chat unread] [Combat turn] [Selection] [Expand active tab]|
+--------------------------------------------------------------------------------------+
| StatusRail persistent                                                                     |
+--------------------------------------------------------------------------------------+
```

## Minimum supported width (`900px - 1023px`)

```text
+----------------------------------------------------------------------------+
| TopBar compact with overflow                                               |
+----------------------------------------------------------------------------+
| LeftRail icon-only |                 Map Canvas                            |
+----------------------------------------------------------------------------+
| RightDrawer summary toggle | BottomTray summary toggle                     |
+----------------------------------------------------------------------------+
| StatusRail (always visible) + constrained layout notice if needed          |
+----------------------------------------------------------------------------+
```

## Compact-state content minimums
- Chat compact: unread count and latest activity marker.
- Combat compact: active combatant + turn index/round.
- Selection compact: selected token name + role-relevant badge (owned, enemy, neutral).

## Premium differentiator placeholder
- Scene Presentation Mode (planned only):
  - Hides most chrome, keeps essential status and exit toggle.
  - Shows scene title card/ambience layer.
  - One action to return to tactical shell.
