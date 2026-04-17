from __future__ import annotations

import hashlib
import json

import pytest

from fastapi.testclient import TestClient

from api.schemas import InstallPackRequest
from api_contracts.packs import InstallablePackManifest
from app.services.session_service import CommandContext, SessionPermissionError, SessionService
from net.signaling_service import app


def _manifest_payload() -> dict:
    return {
        'pack_id': 'starter-pack',
        'pack_name': 'Starter Pack',
        'version': '1.0.0',
        'description': 'Core starter content',
        'scenes': [{'template_name': 'Starter Cavern', 'description': 'A simple cave map'}],
        'actors': [{'actor_id': 'pack-hero', 'name': 'Pack Hero', 'character_class': 'Fighter', 'level': 1, 'hit_points': 10, 'items': []}],
        'journals': [{'entry_id': 'j-pack-1', 'title': 'Lore', 'content': 'Ancient lore'}],
        'handouts': [{'handout_id': 'h-pack-1', 'title': 'Map Scrap', 'body': 'A torn map'}],
        'macros': [{'macro_id': 'm-pack-1', 'name': 'Battle Cry', 'template': '{actor} shouts!', 'created_at': '2026-01-01T00:00:00Z', 'updated_at': '2026-01-01T00:00:00Z'}],
        'templates': [{'roll_template_id': 'rt-pack-1', 'name': 'Starter Attack', 'template': '{actor} attacks', 'action_blocks': {}, 'created_at': '2026-01-01T00:00:00Z', 'updated_at': '2026-01-01T00:00:00Z'}],
        'assets': [{'asset_id': 'asset-pack-1', 'name': 'Torch', 'asset_type': 'stamp', 'uri': 'packs://torch.png', 'tags': [], 'license': None}],
        'plugins': [{'name': 'StarterHooks', 'version': '1.0.0', 'capabilities': ['macro:run']}],
    }


def _checksum(manifest: dict) -> str:
    InstallablePackManifest.model_validate(manifest)
    canonical = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()


def test_install_pack_request_rejects_short_checksum() -> None:
    with pytest.raises(Exception):
        InstallPackRequest(manifest={'pack_id': 'x'}, checksum_sha256='abc')


def test_module_pack_install_enable_disable_lifecycle() -> None:
    service = SessionService()
    session = service.create_session('Pack Test', 'gm-peer')
    session_id = session['session_id']
    command = CommandContext(actor_peer_id='gm-peer', actor_role='GM', idempotency_key='pack-install-1')

    manifest = _manifest_payload()
    install = service.install_module_pack(session_id, manifest=manifest, checksum_sha256=_checksum(manifest), command=command)
    assert install is not None
    assert install['module']['module_id'] == 'starter-pack'
    assert install['module']['enabled'] is True

    listed = service.list_modules(session_id, command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'))
    assert listed is not None
    assert listed[0]['module_id'] == 'starter-pack'
    assert listed[0]['enabled'] is True

    assert any(entry.get('entry_id') == 'j-pack-1' for entry in service.get_journal_entries(session_id, command=command) or [])
    assert any(item.get('asset_id') == 'asset-pack-1' for item in service.get_asset_library(session_id, command=command) or [])
    assert any(actor.get('actor_id') == 'pack-hero' for actor in service.get_characters(session_id, command=command) or [])

    disabled = service.set_module_enabled(session_id, 'starter-pack', enabled=False, command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'))
    assert disabled is not None
    assert disabled['enabled'] is False

    enabled = service.set_module_enabled(session_id, 'starter-pack', enabled=True, command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'))
    assert enabled is not None
    assert enabled['enabled'] is True


def test_install_pack_rejects_bad_checksum() -> None:
    service = SessionService()
    session = service.create_session('Pack Test', 'gm-peer')
    with pytest.raises(SessionPermissionError, match='checksum'):
        service.install_module_pack(
            session['session_id'],
            manifest=_manifest_payload(),
            checksum_sha256='0' * 64,
            command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'),
        )


def test_module_pack_persists_across_save_load_roundtrip(tmp_path) -> None:
    service = SessionService()
    service.store.base_dir = tmp_path
    session = service.create_session('Pack Persistence', 'gm-peer')
    session_id = session['session_id']

    manifest = _manifest_payload()
    installed = service.install_module_pack(
        session_id,
        manifest=manifest,
        checksum_sha256=_checksum(manifest),
        command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'),
    )
    assert installed is not None
    save_path = service.save(session_id)
    assert save_path is not None

    service.sessions.clear()
    service.campaigns.clear()
    service.engines.clear()

    loaded = service.load(session_id)
    assert loaded is not None
    modules = service.list_modules(session_id, command=CommandContext(actor_peer_id='gm-peer', actor_role='GM'))
    assert modules is not None
    assert any(module.get('module_id') == 'starter-pack' for module in modules)


def test_module_install_api_rejects_integrity_mismatch() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ModuleApiIntegrity", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    response = client.post(
        f"/api/sessions/{session_id}/modules/install",
        json={
            "manifest": _manifest_payload(),
            "checksum_sha256": "0" * 64,
            "command": {"actor_peer_id": "dm", "actor_token": host_token},
        },
    )
    assert response.status_code == 400
    assert "checksum" in str(response.json().get("detail", "")).lower()


def test_module_install_idempotency_key_reuse_with_different_payload_is_rejected() -> None:
    service = SessionService()
    session = service.create_session('Pack Idempotency Guard', 'gm-peer')
    session_id = session['session_id']

    manifest_a = _manifest_payload()
    manifest_b = _manifest_payload()
    manifest_b['pack_name'] = 'Starter Pack Mutated'
    command = CommandContext(actor_peer_id='gm-peer', actor_role='GM', idempotency_key='module-install-key')

    first = service.install_module_pack(session_id, manifest=manifest_a, checksum_sha256=_checksum(manifest_a), command=command)
    assert first is not None
    with pytest.raises(SessionPermissionError, match='Idempotency key reuse'):
        service.install_module_pack(session_id, manifest=manifest_b, checksum_sha256=_checksum(manifest_b), command=command)
