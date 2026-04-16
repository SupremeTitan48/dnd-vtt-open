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

## Restore workflow

Restore a previous backup:

```bash
curl -s -X POST \
  http://127.0.0.1:8000/api/sessions/<SESSION_ID>/restore-backup \
  -H "Content-Type: application/json" \
  -d '{"backup_id":"<BACKUP_ID>","command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

On success, response returns restored `state` for the session.

## Backup API rate limits (configuration)

Backup-related endpoints (backup, restore, prune, export, import) share a per-session, per-peer sliding-window limit.

Environment variables (read at request time; restart not required for in-process changes on next request):

| Variable | Default | Meaning |
|----------|---------|---------|
| `DND_VTT_BACKUP_RATE_LIMIT_MAX` | `5` | Max operations per peer per session in the window |
| `DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS` | `60` | Sliding window length in seconds |

Invalid values fall back to defaults. Values are clamped to safe ranges (minimum 1; max operations capped at 10000; window capped at 86400 seconds).

Example (stricter limits for small hosts):

```bash
export DND_VTT_BACKUP_RATE_LIMIT_MAX=10
export DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS=120
```

## Deployment profile (self-hosted)

For a simple LAN or VPS deployment beyond `scripts/run_modern_ui.sh`:

1. **Environment** – Set backup rate limits if needed (see above). Point the app at a writable data directory by running from the project root so `.sessions/` is stable, or symlink/replace that path in code later.

2. **Backend only (API + WS)** – From the repo root with venv active:

```bash
.venv/bin/uvicorn net.signaling_service:app --host 0.0.0.0 --port 8000
```

3. **Frontend** – Build static assets (`npm --prefix frontend run build`) and serve `frontend/dist` with any static file server, or run `npm --prefix frontend run dev` only for development. Configure the frontend to call the same origin or set your reverse proxy so `/api` routes to the FastAPI app.

4. **Reverse proxy (optional)** – Terminate TLS at nginx or Caddy; enable WebSocket upgrade for `/api/sessions/*/events`. Keep backup and health URLs on the same host as the API unless you adjust CORS and frontend `API_BASE` if customized.

5. **Process supervision** – Use systemd, supervisord, or a container runtime to restart the backend on failure. Rate-limit and backup audit state are in-process memory today; multiple workers need external coordination for those features to behave as a single pool.

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

## Recommended verification before upgrades/deploys

```bash
.venv/bin/python -m ruff check .
.venv/bin/pytest
npm --prefix frontend run test
npm --prefix frontend run build
```
