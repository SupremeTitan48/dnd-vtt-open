from __future__ import annotations

from pathlib import Path

from app.disaster_recovery import run_backup_restore_drill
from app.services.session_service import SessionService
from engine.session_store import SessionStore


def test_backup_restore_drill_reports_successful_roundtrip(tmp_path: Path) -> None:
    service = SessionService(store=SessionStore(tmp_path / ".sessions"))
    created = service.create_session("DR Drill", "dm")
    session_id = str(created["session_id"])

    report = run_backup_restore_drill(
        service,
        session_id=session_id,
        token_id="hero",
        baseline_position=(2, 2),
        changed_position=(7, 7),
    )

    assert report["session_id"] == session_id
    assert report["ok"] is True
    assert report["baseline_position"] == [2, 2]
    assert report["changed_position"] == [7, 7]
    assert report["restored_position"] == [2, 2]
    assert report["restored_revision"] == 1
    assert report["backup_id"]
