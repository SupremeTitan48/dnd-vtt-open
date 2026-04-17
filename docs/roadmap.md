# Roadmap

This file tracks practical implementation status against the architecture roadmap.

## Phase 0 - Stabilization / hardening
- Status: substantially complete
- Delivered:
  - Command/event envelope foundations
  - Revision + idempotency behavior
  - Backend and frontend baseline verification loops

## Phase 1 - Multiplayer correctness + permission baseline
- Status: substantially complete (remaining hardening)
- Delivered:
  - Authoritative command dispatch with conflict handling
  - Role model (`GM`, `AssistantGM`, `Player`, `Observer`)
  - Ownership-aware actor/token mutation checks
  - Read filtering for GM-secret surfaces

## Phase 2 - GM knowledge/content tools
- Status: complete for foundation scope
- Delivered:
  - Journal entries + handouts with share/edit visibility controls
  - Campaign encounter template durability
  - Asset library metadata + map stamping workflow

## Phase 3 - Tactical visibility systems
- Status: complete for current slice
- Delivered:
  - Server-side LOS and per-player visibility filtering
  - Token vision radius controls
  - Frontend visibility masks + ruler/movement budget helper
  - Visibility cache + perf metrics endpoint (`/health/perf`)

## Phase 4 - D&D automation/extensibility
- Status: complete (foundation + closeout hardening)
- Delivered:
  - Macro subsystem (create/list/run + execution audit trail)
  - Roll template subsystem (create/list/render + action blocks + render audit)
  - Plugin subsystem (register/list + capability metadata + hook execution isolation)
  - Frontend control surfaces for all above (GM/AssistantGM only)
- Closed out with:
  - UI failure feedback for macro/roll/plugin async actions.
  - Plugin hook isolation enforced at executor boundary (exception-safe isolation).
  - WS redaction coverage for automation events for non-GM viewers.

### Phase 4 exit criteria
- Macro subsystem stable under success/failure and replay scenarios.
- Roll template subsystem stable with validation and safe render error behavior.
- Plugin subsystem stable with capability validation and failure isolation.
- Permission model verified for automation endpoints and event visibility.
- Frontend admin surfaces aligned with role gates and validation UX.
- CI-local verification green (`ruff`, backend tests, frontend tests, frontend build).

## Phase 5 - Production readiness
- Status: started (initial operational readiness slice)
- Planned:
  - Durable ops tooling (migrations, backups, observability)
  - Deployment profiles and operational runbooks
- Delivered so far:
  - Readiness endpoint (`/health/ready`) with operational checks for session store and event log directories.
  - Migration compatibility status in readiness (`app/migrations/status.py`; schema bounds + per-session version visibility).
  - Session backup/restore; list/prune; portable export/import with SHA-256 verification; GM/AssistantGM gates on backup APIs.
  - Backup audit trail (`/api/sessions/{id}/backups/audit`) and configurable in-memory rate limits (`DND_VTT_BACKUP_RATE_LIMIT_*`).
  - Self-hosted operations runbook (`docs/operations.md`) including health, backup workflows, rate-limit env vars, and deployment notes.
  - Configurable session snapshot backend (`DND_VTT_SESSION_STORE_BACKEND=json|sqlite`) with SQLite durability option.
  - Migration rollout/rollback playbook (`docs/migration-playbook.md`) and deployment templates under `deploy/`.

## Competitive Gap Closure Slices (latest delivery)
- Status: slices 1-4 complete in `next-agent-vtt-gap-closure`.
- Delivered:
  - Slice 1 (character experience): sheet-driven action flow with server-side roll formula construction, advantage/disadvantage + visibility controls, and ownership-safe redaction.
  - Slice 2 (lighting/vision): token light sources, scene lighting presets, vision mode controls, GM map tooling, and replay/event permission filtering.
  - Slice 3 (rich chat): `/me`, `/ooc`, whispers, private roll chat semantics, visibility badges, and websocket/replay redaction guarantees.
  - Slice 4 (module ecosystem): installable pack manifest/contracts, install/list/enable/disable APIs, campaign/session module persistence, and frontend Extensions manager UI.
- Hardening included:
  - chat idempotency isolation by caller identity,
  - stricter session-view redaction of sensitive token metadata,
  - module install integrity parity (canonical checksum/signature verification across frontend/backend).
- Verification:
  - `python3 -m pytest -q` passed.
  - `npm --prefix frontend test` passed.
  - `npm --prefix frontend run build` passed.
