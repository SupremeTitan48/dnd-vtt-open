# Operations Runbook

This runbook covers the minimum operational workflow for self-hosted development or small-table deployments.

## Start services

1. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
npm --prefix frontend install
```

2. Start backend + frontend:

```bash
bash scripts/run_modern_ui.sh
```

3. Verify endpoints:
- Backend API: `http://127.0.0.1:8000`
- Frontend UI: `http://127.0.0.1:5173`
- API docs: `http://127.0.0.1:8000/docs`

## Health checks

Run:

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/health/ready
curl -s http://127.0.0.1:8000/health/perf
curl -s http://127.0.0.1:8000/health/ops
curl -s http://127.0.0.1:8000/metrics
```

Expected:
- `/health` returns `{"ok": true}`.
- `/health/ready` returns `ok=true` and passing checks for:
  - `session_store_dir`
  - `event_log_dir`
  - `migration_compatibility`
- `/health/perf` returns visibility metrics with `ok=true`.
- `/health/ops` returns operational metrics with `ok=true`, including:
  - `backup_audit_events_total`
  - `backup_audit_actions`
  - `backup_rate_limit_config`
- `/metrics` returns Prometheus-style plaintext gauges/counters for:
  - active sessions
  - visibility cache hit/miss counts
  - backup audit totals/by-action
  - configured backup rate-limit window values

## Backup workflow

For session `<SESSION_ID>`:

```bash
curl -s -X POST http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backup \
  -H "Content-Type: application/json" \
  -d '{"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Response includes:
- `backup_id`
- `backup_path`

Store `backup_id` for restores and copy backup artifacts off-host when needed.

List backups for a session:

```bash
curl -s "http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups?actor_peer_id=<GM_PEER_ID>&actor_token=<GM_TOKEN>"
```

List backup audit records:

```bash
curl -s "http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups/audit?actor_peer_id=<GM_PEER_ID>&actor_token=<GM_TOKEN>"
```

Prune old backups while keeping the most recent N:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups/prune \
  -H "Content-Type: application/json" \
  -d '{"keep_latest":5,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Prune backups older than a maximum age (in days):

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups/prune-by-age \
  -H "Content-Type: application/json" \
  -d '{"max_age_days":30,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Export a backup payload with integrity checksum:

```bash
curl -s "http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups/<BACKUP_ID>/export?actor_peer_id=<GM_PEER_ID>&actor_token=<GM_TOKEN>"
```

Import a portable backup payload (with checksum verification):

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backups/import \
  -H "Content-Type: application/json" \
  -d '{"backup": <EXPORTED_BACKUP_JSON>, "checksum_sha256":"<CHECKSUM>", "command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

If backup signing is enabled, include `signature_hmac_sha256` from export response in import requests.

Guardrails:
- Backup import payloads above `DND_VTT_BACKUP_IMPORT_MAX_BYTES` are rejected with `400` (default `256000`).

## Restore workflow

Restore a previous backup:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/restore-backup \
  -H "Content-Type: application/json" \
  -d '{"backup_id":"<BACKUP_ID>","command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

On success, response returns restored `state` for the session.

## Migration workflow

Check pending schema migrations without mutating session state:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/migrate \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Apply pending schema migrations:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/migrate \
  -H "Content-Type: application/json" \
  -d '{"dry_run":false,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Notes:
- Migration endpoint requires GM or AssistantGM identity.
- Results include `from_schema_version`, `to_schema_version`, `migrated`, and `applied_migrations`.
- Dry-run reports planned migrations only and does not mutate session state.
- Backup/migration operations also emit structured JSON log events to logger `dnd_vtt.ops`.

## Backup API rate limits (configuration)

Backup-related endpoints (backup, restore, prune, export, import) share a per-session, per-peer sliding-window limit.

Environment variables (read at request time; restart not required for in-process changes on next request):

| Variable | Default | Meaning |
|----------|---------|---------|
| `DND_VTT_BACKUP_RATE_LIMIT_MAX` | `5` | Max operations per peer per session in the window |
| `DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length in seconds |
| `DND_VTT_BACKUP_IMPORT_MAX_BYTES` | `256000` | Maximum accepted JSON payload size for backup import |
| `DND_VTT_BACKUP_SIGNING_SECRET` | _unset_ | Optional HMAC secret for signed backup export/import authenticity checks |

Invalid values fall back to defaults. Values are clamped to safe ranges (minimum 1; max operations capped at 10000; window capped at 86400 seconds).

Example (stricter limits for small hosts):

```bash
export DND_VTT_BACKUP_RATE_LIMIT_MAX=10
export DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS=120
```

## Ops state backend (audit + rate limits)

Backup audit records and backup API rate-limit counters can use either in-memory state (single process) or SQLite (shared across multiple processes on the same host/filesystem).

Environment variables:

| Variable | Default | Meaning |
|----------|---------|---------|
| `DND_VTT_OPS_STATE_BACKEND` | _empty_ (`in-memory`) | Set to `sqlite` to persist/shared ops state |
| `DND_VTT_OPS_STATE_SQLITE_PATH` | `.sessions/ops_state.db` | SQLite file path used when backend is `sqlite` |

### Single-worker development

In-memory backend is fine for local runs:

```bash
unset DND_VTT_OPS_STATE_BACKEND
unset DND_VTT_OPS_STATE_SQLITE_PATH
```

### Multi-worker on one host

Use SQLite so all workers share the same backup audit/rate-limit state:

```bash
export DND_VTT_OPS_STATE_BACKEND=sqlite
export DND_VTT_OPS_STATE_SQLITE_PATH=/var/lib/dnd-vtt/ops_state.db
```

If you use multiple workers/containers, ensure every worker points to the same writable SQLite file path on shared storage.

## Deployment profile (self-hosted)

For a simple LAN or VPS deployment beyond `scripts/run_modern_ui.sh`:

1. **Environment** – Set backup rate limits if needed (see above). Point the app at a writable data directory by running from the project root so `.sessions/` is stable, or symlink/replace that path in code later.

2. **Backend only (API + WS)** – From the repo root with venv active:

```bash
.venv/bin/uvicorn net.signaling_service:app --host 0.0.0.0 --port 8000
```

3. **Frontend** – Build static assets (`npm --prefix frontend run build`) and serve `frontend/dist` with any static file server, or run `npm --prefix frontend run dev` only for development. Configure the frontend to call the same origin or set your reverse proxy so `/api` routes to the FastAPI app.

4. **Reverse proxy (optional)** – Terminate TLS at nginx or Caddy; enable WebSocket upgrade for `/api/sessions/*/events`. Keep backup and health URLs on the same host as the API unless you adjust CORS and frontend `API_BASE` if customized.

5. **Process supervision** – Use systemd, supervisord, or a container runtime to restart the backend on failure. For multi-worker setups, configure `DND_VTT_OPS_STATE_BACKEND=sqlite` so backup audit and backup rate-limit behavior stays consistent across workers on the same host/filesystem.

### Production templates

- Container profile: `deploy/docker-compose.yml` + `deploy/Dockerfile.backend`
- Systemd profile: `deploy/dnd-vtt.service`
- Reverse proxy baseline: `deploy/nginx.conf.example`

### Durable session backend profile

Use SQLite-backed session snapshots in production profiles:

```bash
export DND_VTT_SESSION_STORE_BACKEND=sqlite
export DND_VTT_SESSION_STORE_DIR=/var/lib/dnd-vtt/sessions
export DND_VTT_SESSION_STORE_SQLITE_PATH=/var/lib/dnd-vtt/sessions/sessions.db
```

This keeps snapshot persistence durable while preserving existing backup/event workflows.

## Troubleshooting quick checks

- `404 Session not found` on backup:
  - Confirm session exists and has been created/joined.
- `404 Backup not found` on restore:
  - Verify `backup_id` and that backup files exist under `.sessions/backups/`.
- `403 Backup does not match session id`:
  - Use a backup created for that same `session_id`.
- `429 backup operation rate limit exceeded`:
  - Reduce burst backup/export/import activity and retry after the current rate-limit window.
- `migration_compatibility=false` in `/health/ready`:
  - Inspect `migration.session_versions` and reconcile out-of-range schema versions before continuing.

## Disaster-recovery drill

Validate backup/restore integrity for an existing session:

```bash
.venv/bin/python scripts/run_disaster_recovery_drill.py <SESSION_ID>
```

Exit behavior:
- `0` when the token position roundtrip restores correctly.
- `1` when restore verification fails.

The script prints a JSON report containing `backup_id`, baseline/changed/restored positions, and restored revision.

## Upgrade / rollback playbook

Use `docs/migration-playbook.md` for full migration rollout and rollback procedures.

## Recommended verification before upgrades/deploys

```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run test
npm --prefix frontend run build
```
