from app.backup_rate_limit_config import get_backup_rate_limit_config


def test_default_backup_rate_limit_config(monkeypatch) -> None:
    monkeypatch.delenv("DND_VTT_BACKUP_RATE_LIMIT_MAX", raising=False)
    monkeypatch.delenv("DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS", raising=False)
    max_ops, window = get_backup_rate_limit_config()
    assert max_ops == 5
    assert window == 60


def test_backup_rate_limit_config_from_env(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_MAX", "12")
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS", "120")
    max_ops, window = get_backup_rate_limit_config()
    assert max_ops == 12
    assert window == 120


def test_backup_rate_limit_config_invalid_env_falls_back(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_MAX", "not-a-number")
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS", "also-bad")
    max_ops, window = get_backup_rate_limit_config()
    assert max_ops == 5
    assert window == 60


def test_backup_rate_limit_config_clamps_extremes(monkeypatch) -> None:
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_MAX", "0")
    monkeypatch.setenv("DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS", "0")
    max_ops, window = get_backup_rate_limit_config()
    assert max_ops == 1
    assert window == 1
