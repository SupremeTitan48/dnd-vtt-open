# Changelog

## 2026-04-16 - Phase 5 Production Readiness Completion

### Operations and observability
- Added readiness/performance/ops health coverage (`/health/ready`, `/health/perf`, `/health/ops`) and Prometheus-style metrics export (`/metrics`).
- Added structured JSON operational logs for backup and migration events (`dnd_vtt.ops` logger).
- Added configurable backup API rate limiting and shared ops state backend options (`in-memory` or SQLite).

### Backup lifecycle and safety
- Delivered full backup lifecycle: create, restore, list, prune by count, prune by age, export, and import.
- Added checksum validation and optional HMAC signing for portable backup import/export authenticity (`DND_VTT_BACKUP_SIGNING_SECRET`).
- Added backup import abuse guardrails with configurable payload size cap (`DND_VTT_BACKUP_IMPORT_MAX_BYTES`).
- Added backup audit trails and operational counters across backup endpoints.

### Migration and durability
- Added migration compatibility reporting and a privileged migration runner endpoint (`POST /api/sessions/{session_id}/migrate`) with dry-run/apply modes.
- Advanced schema migration baseline to include v2 and v3 metadata normalization steps.
- Added configurable session snapshot durability backend (`json` or SQLite) for production profiles.
- Added migration rollout/rollback playbook (`docs/migration-playbook.md`).

### Production deployment artifacts
- Added production templates under `deploy/`:
  - `Dockerfile.backend`
  - `docker-compose.yml`
  - `dnd-vtt.service` (systemd)
  - `nginx.conf.example`

### Reliability and verification
- Added disaster-recovery drill automation script (`scripts/run_disaster_recovery_drill.py`).
- Maintained green verification gates across backend/frontend lint, tests, and build during all delivery slices.
