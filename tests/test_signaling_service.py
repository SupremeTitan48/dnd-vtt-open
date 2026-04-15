from fastapi.testclient import TestClient
from pathlib import Path

from net.signaling_service import app


def test_session_join_signal_and_relay_ticket() -> None:
    client = TestClient(app)

    created = client.post(
        "/api/sessions",
        json={"session_name": "Roadside Ambush", "host_peer_id": "dm"},
    )
    assert created.status_code == 200
    session_id = created.json()["session_id"]

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    assert "p1" in joined.json()["peers"]
    assert joined.json()["peer_token"]

    payload = {
        "session_id": session_id,
        "sender_id": "dm",
        "target_id": "p1",
        "payload": {"offer": "abc"},
    }
    assert client.post("/api/signal", json=payload).status_code == 200
    polled = client.get("/api/signal/p1")
    assert polled.status_code == 200
    assert len(polled.json()["messages"]) == 1

    ticket = client.post(
        "/api/relay-ticket",
        json={"session_id": session_id, "peer_id": "p1"},
    )
    assert ticket.status_code == 200
    assert ticket.json()["relay_token"]


def test_create_session_returns_host_peer_token() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/sessions",
        json={"session_name": "Tokenized Host", "host_peer_id": "dm"},
    )
    assert created.status_code == 200
    assert created.json()["host_peer_token"]


def test_feature_endpoints_for_import_fog_and_dm_tools() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Feature Test", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    imported = client.post(
        f'/api/sessions/{session_id}/characters/import',
        json={
            "import_format": "json_schema",
            "payload": '{"name":"Nyx","character_class":"Ranger","level":3,"hit_points":22,"items":["Bow"]}',
            "token_id": "nyx",
        },
    )
    assert imported.status_code == 200
    assert imported.json()['token_id'] == 'nyx'

    chars = client.get(f'/api/sessions/{session_id}/characters')
    assert chars.status_code == 200
    assert len(chars.json()['characters']) == 1

    fog = client.post(f'/api/sessions/{session_id}/fog', json={"enabled": True})
    assert fog.status_code == 200

    reveal = client.post(f'/api/sessions/{session_id}/reveal-cell', json={"x": 1, "y": 1})
    assert reveal.status_code == 200

    notes = client.put(f'/api/sessions/{session_id}/notes', json={"notes": "Remember to pace combat."})
    assert notes.status_code == 200

    template = client.post(
        f'/api/sessions/{session_id}/encounter-templates',
        json={"template_name": "Boss Intro", "description": "Monologue then initiative"},
    )
    assert template.status_code == 200


def test_map_tool_endpoints() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "MapTools", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    terrain = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={"x": 1, "y": 1, "terrain_type": "water"},
    )
    assert terrain.status_code == 200

    blocked = client.post(f'/api/sessions/{session_id}/toggle-blocked', json={"x": 2, "y": 2})
    assert blocked.status_code == 200

    asset = client.post(
        f'/api/sessions/{session_id}/stamp-asset',
        json={"x": 3, "y": 3, "asset_id": "tree"},
    )
    assert asset.status_code == 200

    state = client.get(f'/api/sessions/{session_id}/state').json()['state']['map']
    assert state['terrain_tiles']['1:1'] == 'water'
    assert [2, 2] in state['blocked_cells']
    assert state['asset_stamps']['3:3'] == 'tree'


def test_revision_conflict_and_gm_permission() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Concurrency", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    move_ok = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 1, "y": 1, "command": {"expected_revision": 0, "idempotency_key": "cmd-1"}},
    )
    assert move_ok.status_code == 200
    assert move_ok.json()['state']['revision'] == 1

    move_conflict = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 2, "y": 2, "command": {"expected_revision": 0, "idempotency_key": "cmd-2"}},
    )
    assert move_conflict.status_code == 409

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200

    forbidden = client.post(
        f'/api/sessions/{session_id}/fog',
        json={"enabled": True, "command": {"actor_peer_id": "p1", "expected_revision": 1}},
    )
    assert forbidden.status_code == 403
    assert Path(f'.sessions/events/{session_id}.jsonl').exists()


def test_invalid_command_payload_returns_422() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Invalid", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    invalid_move = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "", "x": -1, "y": 0, "command": {"expected_revision": 0}},
    )
    assert invalid_move.status_code == 422


def test_non_gm_read_visibility_filters_gm_secret_data() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Visibility", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    saved_notes = client.put(f'/api/sessions/{session_id}/notes', json={"notes": "Secret DM note"})
    assert saved_notes.status_code == 200

    player_notes = client.get(f'/api/sessions/{session_id}/notes', params={"actor_peer_id": "p1", "actor_token": p1_token})
    assert player_notes.status_code == 200
    assert player_notes.json()['notes'] == ''

    player_templates = client.get(
        f'/api/sessions/{session_id}/encounter-templates',
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    assert player_templates.status_code == 200
    assert player_templates.json()['encounter_templates'] == []

    player_session = client.get(f'/api/sessions/{session_id}', params={"actor_peer_id": "p1", "actor_token": p1_token})
    assert player_session.status_code == 200
    assert player_session.json().get('notes') == ''
    assert player_session.json().get('encounter_templates') == []
    assert 'peer_roles' not in player_session.json()


def test_player_state_only_includes_owned_actors() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Ownership", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    hero = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 10},
    )
    goblin = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "goblin", "hit_points": 7, "command": {"expected_revision": 1}},
    )
    assert hero.status_code == 200
    assert goblin.status_code == 200

    ownership = client.post(
        f'/api/sessions/{session_id}/actor-ownership',
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
    )
    assert ownership.status_code == 200

    player_state = client.get(f'/api/sessions/{session_id}/state', params={"actor_peer_id": "p1", "actor_token": p1_token})
    assert player_state.status_code == 200
    actors = player_state.json()['state']['actors']
    assert 'hero' in actors
    assert 'goblin' not in actors


def test_non_owner_cannot_mutate_actor_or_token() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "OwnershipWrites", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200

    seed_actor = client.post(f'/api/sessions/{session_id}/actor-state', json={"actor_id": "hero", "hit_points": 10})
    assert seed_actor.status_code == 200

    denied_actor_update = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 9, "command": {"actor_peer_id": "p1", "expected_revision": 1}},
    )
    assert denied_actor_update.status_code == 403

    denied_token_move = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 1, "y": 1, "command": {"actor_peer_id": "p1", "expected_revision": 1}},
    )
    assert denied_token_move.status_code == 403

    assigned = client.post(
        f'/api/sessions/{session_id}/actor-ownership',
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 1}},
    )
    assert assigned.status_code == 200

    allowed_actor_update = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 8, "command": {"actor_peer_id": "p1", "expected_revision": 2}},
    )
    assert allowed_actor_update.status_code == 200

    allowed_move = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 2, "y": 2, "command": {"actor_peer_id": "p1", "expected_revision": 3}},
    )
    assert allowed_move.status_code == 200


def test_observer_role_is_read_only() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Observer", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p2"})
    assert joined.status_code == 200
    p2_token = joined.json()['peer_token']

    role_set = client.post(
        f'/api/sessions/{session_id}/roles',
        json={"peer_id": "p2", "role": "Observer", "command": {"expected_revision": 0}},
    )
    assert role_set.status_code == 200

    observer_write = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 1, "y": 1, "command": {"actor_peer_id": "p2", "expected_revision": 1}},
    )
    assert observer_write.status_code == 403

    observer_read = client.get(f'/api/sessions/{session_id}/state', params={"actor_peer_id": "p2", "actor_token": p2_token})
    assert observer_read.status_code == 200


def test_non_gm_character_list_is_filtered_by_actor_ownership() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "CharacterVisibility", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    import_hero = client.post(
        f'/api/sessions/{session_id}/characters/import',
        json={
            "import_format": "json_schema",
            "payload": '{"name":"Hero","character_class":"Fighter","level":3,"hit_points":28,"items":["Sword"]}',
            "token_id": "hero",
            "command": {"expected_revision": 0},
        },
    )
    import_goblin = client.post(
        f'/api/sessions/{session_id}/characters/import',
        json={
            "import_format": "json_schema",
            "payload": '{"name":"Goblin","character_class":"Rogue","level":1,"hit_points":7,"items":["Dagger"]}',
            "token_id": "goblin",
            "command": {"expected_revision": 1},
        },
    )
    assert import_hero.status_code == 200
    assert import_goblin.status_code == 200

    assign_owner = client.post(
        f'/api/sessions/{session_id}/actor-ownership',
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
    )
    assert assign_owner.status_code == 200

    player_characters = client.get(f'/api/sessions/{session_id}/characters', params={"actor_peer_id": "p1", "actor_token": p1_token})
    assert player_characters.status_code == 200
    names = [character['name'] for character in player_characters.json()['characters']]
    assert names == ["Hero"]


def test_duplicate_idempotency_key_returns_cached_result_without_revision_increment() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Idempotency", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    first = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={
            "token_id": "hero",
            "x": 4,
            "y": 4,
            "command": {"expected_revision": 0, "idempotency_key": "same-op"},
        },
    )
    assert first.status_code == 200
    assert first.json()['state']['revision'] == 1
    assert first.json()['state']['map']['token_positions']['hero'] == [4, 4]

    duplicate = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={
            "token_id": "hero",
            "x": 9,
            "y": 9,
            "command": {"expected_revision": 1, "idempotency_key": "same-op"},
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()['state']['revision'] == 1
    assert duplicate.json()['state']['map']['token_positions']['hero'] == [4, 4]

    state = client.get(f'/api/sessions/{session_id}/state')
    assert state.status_code == 200
    assert state.json()['state']['revision'] == 1

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    token_moved_events = [event for event in replay.json()['events'] if event.get('event_type') == 'token_moved']
    assert len(token_moved_events) == 1


def test_players_cannot_control_combat_flow_but_assistant_gm_can() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "CombatPerms", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined_player = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    joined_assistant = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "agm"})
    assert joined_player.status_code == 200
    assert joined_assistant.status_code == 200

    role_set = client.post(
        f'/api/sessions/{session_id}/roles',
        json={"peer_id": "agm", "role": "AssistantGM", "command": {"expected_revision": 0}},
    )
    assert role_set.status_code == 200

    player_initiative = client.post(
        f'/api/sessions/{session_id}/initiative',
        json={"order": ["hero"], "command": {"actor_peer_id": "p1", "expected_revision": 1}},
    )
    assert player_initiative.status_code == 403

    assistant_initiative = client.post(
        f'/api/sessions/{session_id}/initiative',
        json={"order": ["hero"], "command": {"actor_peer_id": "agm", "expected_revision": 1}},
    )
    assert assistant_initiative.status_code == 200

    player_next_turn = client.post(
        f'/api/sessions/{session_id}/next-turn',
        json={"command": {"actor_peer_id": "p1", "expected_revision": 2}},
    )
    assert player_next_turn.status_code == 403

    assistant_next_turn = client.post(
        f'/api/sessions/{session_id}/next-turn',
        json={"command": {"actor_peer_id": "agm", "expected_revision": 2}},
    )
    assert assistant_next_turn.status_code == 200


def test_non_gm_roles_cannot_mutate_map_tools() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "MapPolicy", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined_player = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    joined_observer = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "obs"})
    assert joined_player.status_code == 200
    assert joined_observer.status_code == 200

    observer_role = client.post(
        f'/api/sessions/{session_id}/roles',
        json={"peer_id": "obs", "role": "Observer", "command": {"expected_revision": 0}},
    )
    assert observer_role.status_code == 200

    player_map_edit = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={"x": 4, "y": 4, "terrain_type": "forest", "command": {"actor_peer_id": "p1", "expected_revision": 1}},
    )
    assert player_map_edit.status_code == 403

    observer_map_edit = client.post(
        f'/api/sessions/{session_id}/toggle-blocked',
        json={"x": 2, "y": 2, "command": {"actor_peer_id": "obs", "expected_revision": 1}},
    )
    assert observer_map_edit.status_code == 403


def test_observer_can_read_session_state_and_characters_but_only_visible_owned_data() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ObserverRead", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join_observer = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "obs"})
    assert join_observer.status_code == 200
    observer_token = join_observer.json()['peer_token']

    set_observer_role = client.post(
        f'/api/sessions/{session_id}/roles',
        json={"peer_id": "obs", "role": "Observer", "command": {"expected_revision": 0}},
    )
    assert set_observer_role.status_code == 200

    import_hero = client.post(
        f'/api/sessions/{session_id}/characters/import',
        json={
            "import_format": "json_schema",
            "payload": '{"name":"Hero","character_class":"Fighter","level":3,"hit_points":28,"items":["Sword"]}',
            "token_id": "hero",
            "command": {"expected_revision": 1},
        },
    )
    assert import_hero.status_code == 200

    session_view = client.get(f'/api/sessions/{session_id}', params={"actor_peer_id": "obs", "actor_token": observer_token})
    assert session_view.status_code == 200
    assert session_view.json().get('notes') == ''
    assert session_view.json().get('encounter_templates') == []

    state_view = client.get(f'/api/sessions/{session_id}/state', params={"actor_peer_id": "obs", "actor_token": observer_token})
    assert state_view.status_code == 200
    assert state_view.json()['state']['actors'] == {}

    character_view = client.get(f'/api/sessions/{session_id}/characters', params={"actor_peer_id": "obs", "actor_token": observer_token})
    assert character_view.status_code == 200
    assert character_view.json()['characters'] == []


def test_player_cannot_escalate_permissions_by_spoofing_actor_role() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "RoleSpoof", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    spoofed_map_edit = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={
            "x": 2,
            "y": 3,
            "terrain_type": "lava",
            "command": {"actor_peer_id": "p1", "actor_role": "GM", "expected_revision": 0},
        },
    )
    assert spoofed_map_edit.status_code == 403

    spoofed_notes_read = client.get(
        f'/api/sessions/{session_id}/notes',
        params={"actor_peer_id": "p1", "actor_token": p1_token, "actor_role": "GM"},
    )
    assert spoofed_notes_read.status_code == 200
    assert spoofed_notes_read.json()['notes'] == ''


def test_read_endpoints_require_valid_actor_token_for_peer_context() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ReadTokenAuth", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200

    denied_state = client.get(f'/api/sessions/{session_id}/state', params={"actor_peer_id": "p1", "actor_token": "invalid"})
    denied_session = client.get(f'/api/sessions/{session_id}', params={"actor_peer_id": "p1", "actor_token": "invalid"})

    assert denied_state.status_code == 403
    assert denied_session.status_code == 403
