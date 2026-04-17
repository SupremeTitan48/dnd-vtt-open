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

## Run (Electron desktop app)
```bash
bash scripts/run_desktop.sh
```

- Launches Electron desktop shell.
- Automatically starts bundled local backend (`uvicorn`) and frontend dev renderer.
- Desktop runtime uses loopback API/WS targets without manual browser setup.

## Legacy fallback (Tkinter)
```bash
bash scripts/run_legacy_tk.sh
```

## Tests and builds
```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run build
npm --prefix desktop-electron run dist
```

## Architecture
See `docs/architecture.md` and `docs/roadmap.md`.
For operations workflows, see `docs/operations.md`.
For upgrade/rollback procedures, see `docs/migration-playbook.md`.
For release history, see `CHANGELOG.md`.

## Phase 4 status (roadmap alignment)
- **Status:** complete (foundation + closeout hardening). Details: `docs/roadmap.md`.
- Completed through previous phases:
  - Phase 0/1 foundations: revisioned command flow, event envelopes, idempotency, conflict handling, role/ownership policy checks.
  - Phase 2 content entities: journal entries, handouts, encounter templates, asset library with share visibility controls.
  - Phase 3 tactical systems: server-authoritative LOS/visibility, token vision radius, ruler/movement budget aid, visibility cache/perf metrics.
- Phase 4 delivered:
  - Macros, roll templates, plugins (API + audit + WS/replay), permission gates, replay redaction, frontend GM/AssistantGM panels with validation and tests.
  - Closeout: async failure feedback in panels, plugin executor isolation, extra WS redaction coverage for automation events.

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

## Phase 5 status (production readiness)
- **Status:** complete for roadmap production-readiness scope.
- Delivered:
  - Added `/health/ready` readiness endpoint for basic operational checks.
  - Added `/health/ops` operational endpoint for backup audit/rate-limit metrics.
  - Added `/metrics` endpoint for Prometheus-style operational export.
  - Readiness checks currently verify writable session store and event log directories.
  - Added backup/restore APIs for session snapshots and metadata recovery.
  - Added backup retention APIs for listing/pruning stored backups (count-based and age-based).
  - Added portable backup export/import APIs with checksum validation.
  - Added GM/AssistantGM permission gates for all backup management operations.
  - Added backup operation audit records and configurable backup API rate limiting (`DND_VTT_BACKUP_RATE_LIMIT_*` env vars; see `docs/operations.md`).
  - Added backup import payload size guardrail (oversized imports rejected).
  - Added optional HMAC-signed backup export/import authenticity validation (`DND_VTT_BACKUP_SIGNING_SECRET`).
  - Added migration compatibility reporting in readiness responses (current schema version now includes v3 metadata normalization).
  - Added a privileged session migration runner endpoint (`POST /api/sessions/{session_id}/migrate`) with dry-run and apply modes.
  - Added structured JSON ops logging for backup and migration actions (`dnd_vtt.ops` logger).
  - Added disaster-recovery drill script for backup/restore roundtrip validation (`scripts/run_disaster_recovery_drill.py`).
  - Added configurable durable session store backend (`json`/`sqlite`) and production deployment templates (`deploy/`).
