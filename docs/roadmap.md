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
- Status: in progress
- Delivered:
  - Macro subsystem (create/list/run + execution audit trail)
  - Roll template subsystem (create/list/render + action blocks + render audit)
  - Plugin subsystem (register/list + capability metadata + hook execution isolation)
  - Frontend control surfaces for all above (GM/AssistantGM only)
- Next:
  - Expand failure/contract tests and stricter capability validation
  - UX feedback improvements for execution outcomes
  - Final closeout: short release note and migration notes for API consumers

### Phase 4 exit criteria
- Macro subsystem stable under success/failure and replay scenarios.
- Roll template subsystem stable with validation and safe render error behavior.
- Plugin subsystem stable with capability validation and failure isolation.
- Permission model verified for automation endpoints and event visibility.
- Frontend admin surfaces aligned with role gates and validation UX.
- CI-local verification green (`ruff`, backend tests, frontend tests, frontend build).

## Phase 5 - Production readiness
- Status: not started
- Planned:
  - Durable ops tooling (migrations, backups, observability)
  - Deployment profiles and operational runbooks
