import json
from pathlib import Path
from typing import Union

REQUIRED_MANIFEST_FIELDS = {"pack_name", "license_id", "attribution", "source_url", "content_type"}


class PackValidationError(ValueError):
    pass


def load_pack_manifest(path: Union[str, Path]) -> dict:
    payload = json.loads(Path(path).read_text())
    missing = REQUIRED_MANIFEST_FIELDS.difference(payload)
    if missing:
        raise PackValidationError(f"Missing manifest fields: {sorted(missing)}")
    return payload
