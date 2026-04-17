# Onboarding Flows

## Design goals
- Keep onboarding to 3-5 steps per role.
- Anchor guidance to live UI elements instead of static screenshots.
- Make flows skippable and replayable.
- Include guided sandbox/sample encounter path.

## Host onboarding (4 steps)
1. Create session
   - Prompt for session name and host identity.
   - Confirm role as `GM` (with optional Host/Admin capability note).
2. Load or place map
   - Guided prompt to place first map assets or load saved state.
   - Highlight map tools region.
3. Invite players
   - Show session ID/share action in top bar.
   - Explain join flow and role assignment quick path.
4. Start sample encounter
   - Spawn sample tokens.
   - Open combat tray and run first turn guidance.

## Player onboarding (4 steps)
1. Join session
   - Enter session code and player identity.
   - Confirm role as `Player`.
2. Select character/token
   - Highlight token selection and ownership cues.
3. Learn core controls
   - Move token, quick measure, chat prompt, end-turn awareness.
4. Run guided sandbox move
   - Mini objective: move, inspect, and acknowledge turn state.

## Replayability and dismissal
- Persist onboarding completion per role and peer identifier.
- Allow replay from help/tutorial entry.
- Dismissed steps can be resumed from step list.

## Tooltip/anchor requirements
- Each step targets real selectors in current shell:
  - top bar role/session chips,
  - left rail tool controls,
  - map canvas,
  - right drawer summary,
  - bottom tray summary tabs.
- If anchor missing due to responsive mode, onboarding should:
  - switch to compact-friendly instruction variant, or
  - prompt user to open required panel.

## Failure-aware onboarding
- If backend/realtime issues occur mid-onboarding:
  - pause progression,
  - surface status rail explanation,
  - provide retry and recovery link.
