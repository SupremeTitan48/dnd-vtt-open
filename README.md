# DND VTT

Open-source, modular, Python-first virtual tabletop MVP focused on accessible online play.

## Current default UI
The project now defaults to a modern web UI stack:
- React + Vite frontend (`frontend/`)
- FastAPI backend API (`net/signaling_service.py` + `api/`)
- Websocket session events for live tabletop updates

Legacy Tkinter UI remains available during transition.

## MVP features
- 2D top-down map and token state
- Initiative, HP, conditions, and held item tracking
- Character import normalization
- ORC/OGL-friendly content pack loading
- Session save/load for local DM workflows
- Signaling + relay ticket endpoints for P2P negotiation
- Realtime session event stream (WebSocket)
- Starter tutorial map for DMs

## Development setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
npm --prefix frontend install
```

## Run (default modern UI)
```bash
bash scripts/run_modern_ui.sh
```

- Backend API: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Frontend UI: `http://127.0.0.1:5173`

## Legacy fallback (Tkinter)
```bash
bash scripts/run_legacy_tk.sh
```

## Tests and builds
```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run build
```

## Architecture
See `docs/architecture.md` and `docs/roadmap.md`.

## Phase 4 status (roadmap alignment)
- Completed through previous phases:
  - Phase 0/1 foundations: revisioned command flow, event envelopes, idempotency, conflict handling, role/ownership policy checks.
  - Phase 2 content entities: journal entries, handouts, encounter templates, asset library with share visibility controls.
  - Phase 3 tactical systems: server-authoritative LOS/visibility, token vision radius, ruler/movement budget aid, visibility cache/perf metrics.
- Phase 4 implemented so far:
  - Macro foundation: create/list/run endpoints, execution audit records, WS/replay events.
  - Roll template foundation: create/list/render endpoints with reusable action blocks and render audit records.
  - Plugin foundation: register/list endpoints, capability metadata, hook execution endpoint with isolated failure behavior.
  - Frontend control panels for macros, roll templates, and plugins (GM/AssistantGM only) with input validation and panel tests.
- Next Phase 4 hardening:
  - Expand API/contract tests for additional failure and concurrency edges.
  - Tighten capability and payload validation semantics.
  - Improve UX feedback for execution and failure states.

## Phase 4 exit checklist
- [x] Macro foundation: create/list/run, audit records, WS/replay events.
- [x] Roll template foundation: create/list/render, action blocks, audit records, WS/replay events.
- [x] Plugin foundation: register/list, capability metadata, hook execution with isolated failure behavior.
- [x] Permission gates: GM/AssistantGM-only mutation and reads for automation/extensibility surfaces.
- [x] Replay/view filtering: non-GM redaction for macro/roll/plugin event payloads.
- [x] Input guardrails: bounded payload sizes and capability format validation.
- [x] Safe error contracts: render failures avoid leaking sensitive internals.
- [x] Frontend control surfaces: macro/roll/plugin panels wired to backend APIs.
- [x] Frontend UX safeguards: role-based panel visibility and inline validation feedback.
- [x] Verification loop: backend tests, frontend tests, lint, and frontend build are green.
