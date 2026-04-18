from __future__ import annotations

import os


def get_backup_import_max_bytes() -> int:
    raw_value = os.environ.get("DND_VTT_BACKUP_IMPORT_MAX_BYTES", "256000")
    try:
        parsed = int(raw_value)
    except ValueError:
        parsed = 256000
    return max(16_384, min(parsed, 50_000_000))
