from __future__ import annotations

import os


def get_backup_rate_limit_config() -> tuple[int, int]:
    """Return (max_operations_per_window, window_seconds) for backup API rate limiting.

    Environment:
    - DND_VTT_BACKUP_RATE_LIMIT_MAX: max backup operations per peer per window (default 5)
    - DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS: sliding window (default 60)
    """
    raw_max = os.environ.get("DND_VTT_BACKUP_RATE_LIMIT_MAX", "5")
    raw_window = os.environ.get("DND_VTT_BACKUP_RATE_LIMIT_WINDOW_SECONDS", "60")
    try:
        max_ops = int(raw_max)
    except ValueError:
        max_ops = 5
    try:
        window_seconds = int(raw_window)
    except ValueError:
        window_seconds = 60
    max_ops = max(1, min(max_ops, 10_000))
    window_seconds = max(1, min(window_seconds, 86_400))
    return max_ops, window_seconds
