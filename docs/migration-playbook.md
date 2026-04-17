# Migration Playbook

This playbook defines a repeatable upgrade procedure for session schema migrations.

## Preconditions

- Backend health is green (`/health`, `/health/ready`).
- Backup APIs are reachable and GM credentials are available.
- Current deployment has enough disk space for backup snapshots.

## Step 1: Backup before migration

For each active session:

```bash
curl -s -X POST http://127.0.0.1:8000/api/sessions/<SESSION_ID>/backup \
  -H "Content-Type: application/json" \
  -d '{"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Record resulting `backup_id` values.

## Step 2: Dry-run migration

```bash
curl -s -X POST http://127.0.0.1:8000/api/sessions/<SESSION_ID>/migrate \
  -H "Content-Type: application/json" \
  -d '{"dry_run":true,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Confirm:
- `applied_migrations` contains only expected migration IDs.
- target `to_schema_version` matches rollout expectations.

## Step 3: Apply migration

```bash
curl -s -X POST http://127.0.0.1:8000/api/sessions/<SESSION_ID>/migrate \
  -H "Content-Type: application/json" \
  -d '{"dry_run":false,"command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

Confirm:
- `migrated` is true when work was pending.
- `to_schema_version` equals expected target.

## Step 4: Post-migration verification

- Check `/health/ready` and verify `migration_compatibility=true`.
- Check `/health/ops` and `/metrics` for expected operational counters.
- Execute disaster-recovery drill:

```bash
.venv/bin/python scripts/run_disaster_recovery_drill.py <SESSION_ID>
```

## Rollback procedure

If migration validation fails:

1. Stop mutating traffic to affected session.
2. Restore pre-migration backup:

```bash
curl -s -X POST http://127.0.0.1:8000/api/sessions/<SESSION_ID>/restore-backup \
  -H "Content-Type: application/json" \
  -d '{"backup_id":"<BACKUP_ID>","command":{"actor_peer_id":"<GM_PEER_ID>","actor_token":"<GM_TOKEN>"}}'
```

3. Verify restored state and revision.
4. Review structured `dnd_vtt.ops` logs for migration event details.
5. Re-run migration only after root cause is resolved.
