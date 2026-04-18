from __future__ import annotations

from app.migrations.runner import run_session_migrations


def test_run_session_migrations_applies_v2_and_v3() -> None:
    session = {"session_id": "s1", "host_peer_id": "dm", "schema_version": 1}
    result = run_session_migrations(session, dry_run=False)
    assert result["migrated"] is True
    assert result["to_schema_version"] >= 3
    assert "v2_session_metadata" in result["applied_migrations"]
    assert "v3_role_metadata" in result["applied_migrations"]
    assert session["peer_roles"]["dm"] == "GM"
    assert session["campaign_id"] == "s1"
