from __future__ import annotations

import hashlib
import hmac
import os


def get_backup_signing_secret() -> str | None:
    secret = os.environ.get("DND_VTT_BACKUP_SIGNING_SECRET", "").strip()
    return secret or None


def compute_backup_signature(secret: str, canonical_payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), canonical_payload, hashlib.sha256).hexdigest()
