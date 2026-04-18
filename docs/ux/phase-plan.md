# UX Phase Plan

## Phase 1 (this slice): shell foundation and legibility
- Deliver app shell regions with map-first structure.
- Introduce right drawer and bottom tray with compact summaries.
- Add role policy matrix wiring for player-first defaults.
- Add persistent status rail with precedence/persistence rules.
- Add responsive mode handling for `wideDesktop`, `narrowDesktop`, `minSupportedWidth`.

### Exit criteria
- Existing session host/join/realtime flow remains stable.
- Player experience is visibly simpler than GM/HostAdmin.
- Compact tray/drawer summaries remain useful in expert workflows.
- Status rail correctly resolves simultaneous states.

## Phase 2: contextual workflows and command affordances
- Token HUD quick actions near selection.
- Combat tray to map focus integration.
- Command palette (`Ctrl/Cmd+K`) and shortcut overlay.
- First-use helper tips for core interactions.

### Exit criteria
- Common token/combat flows complete without opening full side panels.
- Keyboard discoverability is available in-context.

## Phase 3: onboarding and guidance maturity
- Role-specific onboarding overlays with replay support.
- Guided sample encounter and sandbox path.
- In-product help entry for replay and troubleshooting.

### Exit criteria
- First-time host/player complete onboarding in <= 5 steps.
- Onboarding survives responsive mode and failure-state interruptions.

## Phase 4: simple fog workflow and premium staging
- Mode/action fog workflow (`hide all`, `reveal`, `re-hide`, `preview player view`).
- Premium scene presentation mode documented and optionally scaffolded.

### Exit criteria
- Fog editing no longer requires dense panel traversal.
- Presentation mode has documented toggles and boundaries.
