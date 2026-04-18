from __future__ import annotations

from app.ops_state_store import SqliteOpsStateStore


def test_sqlite_ops_store_shares_state_across_instances(tmp_path) -> None:
    db_path = tmp_path / "ops_state.db"
    store_a = SqliteOpsStateStore(path=db_path)
    store_b = SqliteOpsStateStore(path=db_path)

    store_a.record_backup_audit("s1", actor_peer_id="dm", action="backup_created", detail={"k": "v"})
    audits = store_b.get_backup_audit("s1")
    assert len(audits) == 1
    assert audits[0]["action"] == "backup_created"
    assert audits[0]["detail"] == {"k": "v"}

    total, actions = store_b.get_backup_audit_summary()
    assert total == 1
    assert actions["backup_created"] == 1


def test_sqlite_ops_store_rate_limit_shared(tmp_path) -> None:
    db_path = tmp_path / "ops_state.db"
    store_a = SqliteOpsStateStore(path=db_path)
    store_b = SqliteOpsStateStore(path=db_path)

    assert store_a.try_acquire_rate_limit("s1", "dm", limit=2, window_seconds=60) is True
    assert store_b.try_acquire_rate_limit("s1", "dm", limit=2, window_seconds=60) is True
    assert store_a.try_acquire_rate_limit("s1", "dm", limit=2, window_seconds=60) is False
