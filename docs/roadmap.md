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
