import pytest

from content.enemy_pack_loader import PackValidationError, load_pack_manifest


def test_manifest_loader_accepts_valid_manifest() -> None:
    payload = load_pack_manifest("packs/starter/manifest_enemy_pack.json")
    assert payload["license_id"] == "ORC"


def test_manifest_loader_rejects_invalid_manifest(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text('{"pack_name": "missing fields"}')
    with pytest.raises(PackValidationError):
        load_pack_manifest(bad)
