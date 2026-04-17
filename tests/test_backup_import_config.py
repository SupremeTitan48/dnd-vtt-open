from __future__ import annotations

from app.backup_import_config import get_backup_import_max_bytes


def test_backup_import_max_bytes_defaults_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("DND_VTT_BACKUP_IMPORT_MAX_BYTES", raising=False)
    assert get_backup_import_max_bytes() == 256000


def test_backup_import_max_bytes_honors_valid_env(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_IMPORT_MAX_BYTES", "512000")
    assert get_backup_import_max_bytes() == 512000


def test_backup_import_max_bytes_falls_back_for_invalid(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_IMPORT_MAX_BYTES", "nope")
    assert get_backup_import_max_bytes() == 256000


def test_backup_import_max_bytes_clamps_range(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_IMPORT_MAX_BYTES", "1")
    assert get_backup_import_max_bytes() == 16_384

    monkeypatch.setenv("DND_VTT_BACKUP_IMPORT_MAX_BYTES", "999999999")
    assert get_backup_import_max_bytes() == 50_000_000
