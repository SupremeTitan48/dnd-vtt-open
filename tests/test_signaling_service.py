from fastapi.testclient import TestClient
from pathlib import Path

from api.http_api import session_service
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


def test_health_perf_reports_visibility_cache_metrics() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "PerfHealth", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    moved = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 5, "y": 5})
    assert moved.status_code == 200
    vis_1 = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "hero", "radius": 5, "command": {"expected_revision": 1}},
    )
    vis_2 = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "hero", "radius": 5, "command": {"expected_revision": 2}},
    )
    assert vis_1.status_code == 200
    assert vis_2.status_code == 200

    perf = client.get('/health/perf')
    assert perf.status_code == 200
    body = perf.json()
    assert body['ok'] is True
    assert isinstance(body['active_sessions'], int)
    assert isinstance(body['visibility_cache_hits'], int)
    assert isinstance(body['visibility_cache_misses'], int)
    assert isinstance(body['sessions'], list)
    assert body['active_sessions'] >= 1
    assert body['visibility_cache_hits'] >= 1
    assert body['visibility_cache_misses'] >= 1
    session_metrics = next(item for item in body['sessions'] if item['session_id'] == session_id)
    assert isinstance(session_metrics['visibility_cache_hits'], int)
    assert isinstance(session_metrics['visibility_cache_misses'], int)
    assert isinstance(session_metrics['blocker_revision'], int)


def test_feature_endpoints_for_import_fog_and_dm_tools() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Feature Test", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

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
        json={
            "template_name": "Boss Intro",
            "description": "Monologue then initiative",
            "command": {"actor_peer_id": "dm", "actor_token": host_token},
        },
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


def test_journal_and_handout_share_visibility_controls() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "JournalShare", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    p1_token = joined.json()['peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    journal = client.post(
        f"/api/sessions/{session_id}/journal-entries",
        json={"title": "Secret Plan", "content": "Only DM sees this initially", "command": host_command},
    )
    handout = client.post(
        f"/api/sessions/{session_id}/handouts",
        json={"title": "Clue", "body": "A sigil carved in stone.", "command": host_command},
    )
    assert journal.status_code == 200
    assert handout.status_code == 200
    journal_id = journal.json()['entry']['entry_id']
    handout_id = handout.json()['handout']['handout_id']

    before_share_journal = client.get(
        f"/api/sessions/{session_id}/journal-entries",
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    before_share_handouts = client.get(
        f"/api/sessions/{session_id}/handouts",
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    assert before_share_journal.status_code == 200
    assert before_share_handouts.status_code == 200
    assert before_share_journal.json()['journal_entries'] == []
    assert before_share_handouts.json()['handouts'] == []

    share_journal = client.post(
        f"/api/sessions/{session_id}/journal-entries/{journal_id}/share",
        json={"shared_roles": ["Player"], "shared_peer_ids": ["p1"], "command": host_command},
    )
    share_handout = client.post(
        f"/api/sessions/{session_id}/handouts/{handout_id}/share",
        json={"shared_roles": ["Player"], "shared_peer_ids": ["p1"], "command": host_command},
    )
    assert share_journal.status_code == 200
    assert share_handout.status_code == 200

    after_share_journal = client.get(
        f"/api/sessions/{session_id}/journal-entries",
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    after_share_handouts = client.get(
        f"/api/sessions/{session_id}/handouts",
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    assert len(after_share_journal.json()['journal_entries']) == 1
    assert len(after_share_handouts.json()['handouts']) == 1


def test_encounter_templates_reuse_across_campaign_sessions() -> None:
    client = TestClient(app)
    first = client.post(
        "/api/sessions",
        json={"session_name": "Campaign A", "host_peer_id": "dm", "campaign_id": "camp-1"},
    )
    first_id = first.json()['session_id']
    first_host_token = first.json()['host_peer_token']

    add_template = client.post(
        f"/api/sessions/{first_id}/encounter-templates",
        json={
            "template_name": "Crypt Start",
            "description": "Undead ambush",
            "command": {"actor_peer_id": "dm", "actor_token": first_host_token},
        },
    )
    assert add_template.status_code == 200
    assert any(t['template_name'] == "Crypt Start" for t in add_template.json()['encounter_templates'])

    second = client.post(
        "/api/sessions",
        json={"session_name": "Campaign B", "host_peer_id": "dm2", "campaign_id": "camp-1"},
    )
    second_id = second.json()['session_id']
    second_host_token = second.json()['host_peer_token']
    templates = client.get(
        f"/api/sessions/{second_id}/encounter-templates",
        params={"actor_peer_id": "dm2", "actor_token": second_host_token},
    )
    assert templates.status_code == 200
    assert any(t['template_name'] == "Crypt Start" for t in templates.json()['encounter_templates'])


def test_asset_library_add_and_list_for_map_workflow() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Assets", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    add_asset = client.post(
        f"/api/sessions/{session_id}/assets",
        json={
            "asset_id": "banner",
            "name": "Battle Banner",
            "asset_type": "stamp",
            "uri": "https://example.com/banner.png",
            "command": host_command,
        },
    )
    assert add_asset.status_code == 200
    assert add_asset.json()['asset']['asset_id'] == "banner"

    list_assets = client.get(
        f"/api/sessions/{session_id}/assets",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    assert list_assets.status_code == 200
    assert any(asset['asset_id'] == "banner" for asset in list_assets.json()['assets'])

    stamp = client.post(
        f"/api/sessions/{session_id}/stamp-asset",
        json={"x": 5, "y": 5, "asset_id": "banner", "command": {"expected_revision": add_asset.json()['revision']}},
    )
    assert stamp.status_code == 200
    assert stamp.json()['state']['map']['asset_stamps']['5:5'] == "banner"


def test_phase2_content_endpoints_require_actor_identity() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "StrictIdentity", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    denied_journal_list = client.get(f"/api/sessions/{session_id}/journal-entries")
    denied_handout_list = client.get(f"/api/sessions/{session_id}/handouts")
    denied_asset_list = client.get(f"/api/sessions/{session_id}/assets")
    denied_template_list = client.get(f"/api/sessions/{session_id}/encounter-templates")

    denied_journal_create = client.post(
        f"/api/sessions/{session_id}/journal-entries",
        json={"title": "Secret", "content": "No actor context"},
    )
    denied_handout_create = client.post(
        f"/api/sessions/{session_id}/handouts",
        json={"title": "Clue", "body": "No actor context"},
    )
    denied_asset_create = client.post(
        f"/api/sessions/{session_id}/assets",
        json={"asset_id": "stone", "name": "Stone", "asset_type": "stamp", "uri": "https://example.com/stone.png"},
    )
    denied_template_create = client.post(
        f"/api/sessions/{session_id}/encounter-templates",
        json={"template_name": "NoAuth", "description": "Should fail without actor"},
    )

    assert denied_journal_list.status_code == 403
    assert denied_handout_list.status_code == 403
    assert denied_asset_list.status_code == 403
    assert denied_template_list.status_code == 403
    assert denied_journal_create.status_code == 403
    assert denied_handout_create.status_code == 403
    assert denied_asset_create.status_code == 403
    assert denied_template_create.status_code == 403


def test_phase2_campaign_content_survives_save_and_load() -> None:
    client = TestClient(app)
    created = client.post(
        '/api/sessions',
        json={"session_name": "StrictDurability", "host_peer_id": "dm", "campaign_id": "strict-camp"},
    )
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    created_journal = client.post(
        f"/api/sessions/{session_id}/journal-entries",
        json={"title": "Lore", "content": "Durable", "command": host_command},
    )
    assert created_journal.status_code == 200

    created_handout = client.post(
        f"/api/sessions/{session_id}/handouts",
        json={"title": "Map", "body": "Durable", "command": host_command},
    )
    assert created_handout.status_code == 200

    created_asset = client.post(
        f"/api/sessions/{session_id}/assets",
        json={
            "asset_id": "durable-banner",
            "name": "Durable Banner",
            "asset_type": "stamp",
            "uri": "https://example.com/durable-banner.png",
            "command": host_command,
        },
    )
    assert created_asset.status_code == 200

    created_template = client.post(
        f"/api/sessions/{session_id}/encounter-templates",
        json={"template_name": "DurableStart", "description": "Durable", "command": host_command},
    )
    assert created_template.status_code == 200

    save_result = client.post(f"/api/sessions/{session_id}/save")
    assert save_result.status_code == 200

    session_service.sessions.pop(session_id, None)
    session_service.engines.pop(session_id, None)
    session_service.campaigns.pop('strict-camp', None)

    load_result = client.post(f"/api/sessions/{session_id}/load")
    assert load_result.status_code == 200

    restored_journals = client.get(
        f"/api/sessions/{session_id}/journal-entries",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    restored_handouts = client.get(
        f"/api/sessions/{session_id}/handouts",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    restored_assets = client.get(
        f"/api/sessions/{session_id}/assets",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    restored_templates = client.get(
        f"/api/sessions/{session_id}/encounter-templates",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )

    assert restored_journals.status_code == 200
    assert restored_handouts.status_code == 200
    assert restored_assets.status_code == 200
    assert restored_templates.status_code == 200
    assert any(entry['title'] == "Lore" for entry in restored_journals.json()['journal_entries'])
    assert any(item['title'] == "Map" for item in restored_handouts.json()['handouts'])
    assert any(item['asset_id'] == "durable-banner" for item in restored_assets.json()['assets'])
    assert any(item['template_name'] == "DurableStart" for item in restored_templates.json()['encounter_templates'])


def test_visibility_recompute_enforces_permissions_and_revision_idempotency() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "VisibilitySlice", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    moved = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 1, "y": 1})
    blocked = client.post(
        f"/api/sessions/{session_id}/toggle-blocked",
        json={"x": 2, "y": 1, "command": {"expected_revision": 1}},
    )
    assert moved.status_code == 200
    assert blocked.status_code == 200

    recompute = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={
            "token_id": "hero",
            "radius": 3,
            "command": {"expected_revision": 2, "idempotency_key": "vision-1"},
        },
    )
    assert recompute.status_code == 200
    assert recompute.json()['state']['revision'] == 3
    visible_cells = {tuple(cell) for cell in recompute.json()['state']['map']['visibility_cells_by_token']['hero']}
    assert (2, 1) in visible_cells
    assert (3, 1) not in visible_cells

    duplicate = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={
            "token_id": "hero",
            "radius": 1,
            "command": {"expected_revision": 3, "idempotency_key": "vision-1"},
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()['state']['revision'] == 3
    duplicate_cells = {tuple(cell) for cell in duplicate.json()['state']['map']['visibility_cells_by_token']['hero']}
    assert duplicate_cells == visible_cells

    stale = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "hero", "radius": 3, "command": {"expected_revision": 2, "idempotency_key": "vision-2"}},
    )
    assert stale.status_code == 409

    join = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join.status_code == 200

    denied = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "hero", "radius": 2, "command": {"actor_peer_id": "p1", "expected_revision": 3}},
    )
    assert denied.status_code == 403


def test_state_visibility_cells_are_filtered_by_owned_tokens_per_player() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "VisibilityOwnership", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join_p1 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    join_p2 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p2"})
    assert join_p1.status_code == 200
    assert join_p2.status_code == 200
    p1_token = join_p1.json()['peer_token']
    p2_token = join_p2.json()['peer_token']

    hero = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 1, "y": 1})
    rogue = client.post(
        f"/api/sessions/{session_id}/move-token",
        json={"token_id": "rogue", "x": 6, "y": 1, "command": {"expected_revision": 1}},
    )
    assert hero.status_code == 200
    assert rogue.status_code == 200

    owner_hero = client.post(
        f"/api/sessions/{session_id}/actor-ownership",
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
    )
    owner_rogue = client.post(
        f"/api/sessions/{session_id}/actor-ownership",
        json={"actor_id": "rogue", "peer_id": "p2", "command": {"expected_revision": 3}},
    )
    assert owner_hero.status_code == 200
    assert owner_rogue.status_code == 200

    vis_hero = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "hero", "radius": 3, "command": {"expected_revision": 4}},
    )
    vis_rogue = client.post(
        f"/api/sessions/{session_id}/recompute-visibility",
        json={"token_id": "rogue", "radius": 3, "command": {"expected_revision": 5}},
    )
    assert vis_hero.status_code == 200
    assert vis_rogue.status_code == 200

    p1_state = client.get(f"/api/sessions/{session_id}/state", params={"actor_peer_id": "p1", "actor_token": p1_token})
    p2_state = client.get(f"/api/sessions/{session_id}/state", params={"actor_peer_id": "p2", "actor_token": p2_token})
    assert p1_state.status_code == 200
    assert p2_state.status_code == 200
    p1_visibility = p1_state.json()['state']['map']['visibility_cells_by_token']
    p2_visibility = p2_state.json()['state']['map']['visibility_cells_by_token']
    assert 'hero' in p1_visibility
    assert 'rogue' not in p1_visibility
    assert 'rogue' in p2_visibility
    assert 'hero' not in p2_visibility


def test_set_token_vision_radius_updates_state_and_enforces_permissions() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "VisionRadius", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join_player = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join_player.status_code == 200

    moved = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 2, "y": 2})
    assert moved.status_code == 200

    set_radius = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "hero", "radius": 4, "command": {"expected_revision": 1}},
    )
    assert set_radius.status_code == 200
    assert set_radius.json()['state']['revision'] == 2
    assert set_radius.json()['state']['map']['vision_radius_by_token']['hero'] == 4
    assert set_radius.json()['state']['map']['visibility_cells_by_token']['hero']

    denied_player = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "hero", "radius": 1, "command": {"actor_peer_id": "p1", "expected_revision": 2}},
    )
    assert denied_player.status_code == 403


def test_phase3_acceptance_two_players_receive_different_visibility_results() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase3Acceptance", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join_p1 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    join_p2 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p2"})
    assert join_p1.status_code == 200
    assert join_p2.status_code == 200
    p1_token = join_p1.json()['peer_token']
    p2_token = join_p2.json()['peer_token']

    hero = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 1, "y": 1})
    rogue = client.post(
        f"/api/sessions/{session_id}/move-token",
        json={"token_id": "rogue", "x": 8, "y": 1, "command": {"expected_revision": 1}},
    )
    assert hero.status_code == 200
    assert rogue.status_code == 200

    owner_hero = client.post(
        f"/api/sessions/{session_id}/actor-ownership",
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
    )
    owner_rogue = client.post(
        f"/api/sessions/{session_id}/actor-ownership",
        json={"actor_id": "rogue", "peer_id": "p2", "command": {"expected_revision": 3}},
    )
    assert owner_hero.status_code == 200
    assert owner_rogue.status_code == 200

    radius_hero = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "hero", "radius": 3, "command": {"expected_revision": 4}},
    )
    radius_rogue = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "rogue", "radius": 1, "command": {"expected_revision": 5}},
    )
    assert radius_hero.status_code == 200
    assert radius_rogue.status_code == 200

    p1_state = client.get(f"/api/sessions/{session_id}/state", params={"actor_peer_id": "p1", "actor_token": p1_token})
    p2_state = client.get(f"/api/sessions/{session_id}/state", params={"actor_peer_id": "p2", "actor_token": p2_token})
    assert p1_state.status_code == 200
    assert p2_state.status_code == 200

    p1_visibility = p1_state.json()['state']['map']['visibility_cells_by_token']
    p2_visibility = p2_state.json()['state']['map']['visibility_cells_by_token']
    assert list(p1_visibility.keys()) == ["hero"]
    assert list(p2_visibility.keys()) == ["rogue"]
    assert len(p1_visibility["hero"]) > len(p2_visibility["rogue"])


def test_phase4_macro_lifecycle_and_audit_events() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4Macros", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    join_player = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join_player.status_code == 200
    p1_token = join_player.json()['peer_token']

    denied_player_create = client.post(
        f"/api/sessions/{session_id}/macros",
        json={
            "name": "PlayerTry",
            "template": "{actor} tries to cast {spell}.",
            "command": {"actor_peer_id": "p1", "actor_token": p1_token},
        },
    )
    assert denied_player_create.status_code == 403

    host_command = {"actor_peer_id": "dm", "actor_token": host_token}
    create_macro = client.post(
        f"/api/sessions/{session_id}/macros",
        json={
            "name": "CastSpell",
            "template": "{actor} casts {spell}.",
            "command": host_command,
        },
    )
    assert create_macro.status_code == 200
    assert create_macro.json()['macro']['name'] == "CastSpell"
    macro_id = create_macro.json()['macro']['macro_id']

    run_macro = client.post(
        f"/api/sessions/{session_id}/macros/{macro_id}/run",
        json={"variables": {"actor": "Nyx", "spell": "Hunter's Mark"}, "command": host_command},
    )
    assert run_macro.status_code == 200
    assert run_macro.json()['result'] == "Nyx casts Hunter's Mark."
    assert run_macro.json()['execution']['actor_peer_id'] == "dm"

    listed = client.get(
        f"/api/sessions/{session_id}/macros",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    assert listed.status_code == 200
    assert len(listed.json()['macros']) == 1
    assert listed.json()['macros'][0]['name'] == "CastSpell"

    replay = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    macro_created = [event for event in replay.json()['events'] if event.get('event_type') == 'macro_created']
    macro_ran = [event for event in replay.json()['events'] if event.get('event_type') == 'macro_ran']
    assert len(macro_created) == 1
    assert len(macro_ran) == 1


def test_phase4_roll_template_lifecycle_and_rendering() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4RollTemplates", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    join_player = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join_player.status_code == 200
    p1_token = join_player.json()['peer_token']

    denied_player_create = client.post(
        f"/api/sessions/{session_id}/roll-templates",
        json={
            "name": "PlayerAttack",
            "template": "{actor} attacks with {attack}.",
            "action_blocks": {"attack": "Longsword"},
            "command": {"actor_peer_id": "p1", "actor_token": p1_token},
        },
    )
    assert denied_player_create.status_code == 403

    host_command = {"actor_peer_id": "dm", "actor_token": host_token}
    create_template = client.post(
        f"/api/sessions/{session_id}/roll-templates",
        json={
            "name": "MeleeAttack",
            "template": "{actor} uses {attack} to roll {roll}.",
            "action_blocks": {"attack": "Longsword", "roll": "1d20+5"},
            "command": host_command,
        },
    )
    assert create_template.status_code == 200
    template_id = create_template.json()['roll_template']['roll_template_id']

    listed = client.get(
        f"/api/sessions/{session_id}/roll-templates",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    assert listed.status_code == 200
    assert len(listed.json()['roll_templates']) == 1
    assert listed.json()['roll_templates'][0]['name'] == "MeleeAttack"

    rendered = client.post(
        f"/api/sessions/{session_id}/roll-templates/{template_id}/render",
        json={"variables": {"actor": "Nyx"}, "command": host_command},
    )
    assert rendered.status_code == 200
    assert rendered.json()['rendered'] == "Nyx uses Longsword to roll 1d20+5."

    replay = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    created_events = [event for event in replay.json()['events'] if event.get('event_type') == 'roll_template_created']
    rendered_events = [event for event in replay.json()['events'] if event.get('event_type') == 'roll_template_rendered']
    assert len(created_events) == 1
    assert len(rendered_events) == 1


def test_phase4_plugin_registration_capabilities_and_failure_isolation() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4Plugins", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    denied_player_register = client.post(
        f"/api/sessions/{session_id}/plugins",
        json={
            "name": "PlayerPlugin",
            "version": "0.1.0",
            "capabilities": ["macro:run"],
            "command": {"actor_peer_id": "p1", "actor_token": p1_token},
        },
    )
    assert denied_player_register.status_code == 403

    host_command = {"actor_peer_id": "dm", "actor_token": host_token}
    register_ok = client.post(
        f"/api/sessions/{session_id}/plugins",
        json={
            "name": "StablePlugin",
            "version": "1.0.0",
            "capabilities": ["macro:run", "roll_template:render"],
            "command": host_command,
        },
    )
    assert register_ok.status_code == 200
    plugin_id = register_ok.json()['plugin']['plugin_id']

    plugin_list = client.get(
        f"/api/sessions/{session_id}/plugins",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    assert plugin_list.status_code == 200
    assert len(plugin_list.json()['plugins']) == 1
    assert plugin_list.json()['plugins'][0]['capabilities'] == ["macro:run", "roll_template:render"]

    hook_ok = client.post(
        f"/api/sessions/{session_id}/plugins/{plugin_id}/hooks/after_event/execute",
        json={"payload": {"event_type": "macro_ran"}, "command": host_command},
    )
    assert hook_ok.status_code == 200
    assert hook_ok.json()['status'] == 'ok'

    hook_fail = client.post(
        f"/api/sessions/{session_id}/plugins/{plugin_id}/hooks/after_event/execute",
        json={"payload": {"event_type": "macro_ran", "simulate_failure": True}, "command": host_command},
    )
    assert hook_fail.status_code == 200
    assert hook_fail.json()['status'] == 'isolated_failure'
    assert 'error' in hook_fail.json()

    state_still_works = client.get(
        f"/api/sessions/{session_id}/state",
        params={"actor_peer_id": "dm", "actor_token": host_token},
    )
    assert state_still_works.status_code == 200

    replay = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    plugin_registered = [event for event in replay.json()['events'] if event.get('event_type') == 'plugin_registered']
    plugin_hook_succeeded = [event for event in replay.json()['events'] if event.get('event_type') == 'plugin_hook_succeeded']
    plugin_hook_failed = [event for event in replay.json()['events'] if event.get('event_type') == 'plugin_hook_failed']
    assert len(plugin_registered) == 1
    assert len(plugin_hook_succeeded) == 1
    assert len(plugin_hook_failed) == 1


def test_phase4_macro_missing_variable_returns_safe_error() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4MacroError", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    macro = client.post(
        f"/api/sessions/{session_id}/macros",
        json={"name": "NeedSpell", "template": "{actor} casts {spell}.", "command": host_command},
    )
    assert macro.status_code == 200
    macro_id = macro.json()['macro']['macro_id']

    run = client.post(
        f"/api/sessions/{session_id}/macros/{macro_id}/run",
        json={"variables": {"actor": "Nyx"}, "command": host_command},
    )
    assert run.status_code == 403
    assert "spell" not in str(run.json())


def test_phase4_roll_template_missing_variable_returns_safe_error() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4RollError", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    created_template = client.post(
        f"/api/sessions/{session_id}/roll-templates",
        json={
            "name": "NeedTarget",
            "template": "{actor} attacks {target}.",
            "action_blocks": {},
            "command": host_command,
        },
    )
    assert created_template.status_code == 200
    template_id = created_template.json()['roll_template']['roll_template_id']

    rendered = client.post(
        f"/api/sessions/{session_id}/roll-templates/{template_id}/render",
        json={"variables": {"actor": "Nyx"}, "command": host_command},
    )
    assert rendered.status_code == 403
    assert "target" not in str(rendered.json())


def test_phase4_non_gm_replay_redacts_macro_roll_and_plugin_events() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4ReplayRedaction", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    created_macro = client.post(
        f"/api/sessions/{session_id}/macros",
        json={"name": "Cast", "template": "{actor} casts {spell}.", "command": host_command},
    )
    macro_id = created_macro.json()['macro']['macro_id']
    client.post(
        f"/api/sessions/{session_id}/macros/{macro_id}/run",
        json={"variables": {"actor": "Nyx", "spell": "Shield"}, "command": host_command},
    )

    created_template = client.post(
        f"/api/sessions/{session_id}/roll-templates",
        json={
            "name": "Attack",
            "template": "{actor} uses {attack}.",
            "action_blocks": {"attack": "Longsword"},
            "command": host_command,
        },
    )
    template_id = created_template.json()['roll_template']['roll_template_id']
    client.post(
        f"/api/sessions/{session_id}/roll-templates/{template_id}/render",
        json={"variables": {"actor": "Nyx"}, "command": host_command},
    )

    registered_plugin = client.post(
        f"/api/sessions/{session_id}/plugins",
        json={"name": "Hooks", "version": "1.0.0", "capabilities": ["macro:run"], "command": host_command},
    )
    plugin_id = registered_plugin.json()['plugin']['plugin_id']
    client.post(
        f"/api/sessions/{session_id}/plugins/{plugin_id}/hooks/after_event/execute",
        json={"payload": {"event_type": "macro_ran", "simulate_failure": True}, "command": host_command},
    )

    replay = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 0, "actor_peer_id": "p1", "actor_token": p1_token},
    )
    assert replay.status_code == 200
    redacted_types = {
        'macro_created',
        'macro_ran',
        'roll_template_created',
        'roll_template_rendered',
        'plugin_registered',
        'plugin_hook_succeeded',
        'plugin_hook_failed',
    }
    for event in replay.json()['events']:
        if event.get('event_type') in redacted_types:
            assert event.get('payload') == {}


def test_phase4_request_guardrails_reject_oversized_payloads() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4Guardrails", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    oversized_macro = client.post(
        f"/api/sessions/{session_id}/macros",
        json={"name": "X" * 81, "template": "ok", "command": host_command},
    )
    oversized_template = client.post(
        f"/api/sessions/{session_id}/roll-templates",
        json={
            "name": "Attack",
            "template": "ok",
            "action_blocks": {f"k{i}": "v" for i in range(40)},
            "command": host_command,
        },
    )
    oversized_plugin_caps = client.post(
        f"/api/sessions/{session_id}/plugins",
        json={
            "name": "Plugin",
            "version": "1.0.0",
            "capabilities": [f"domain{i}:run" for i in range(40)],
            "command": host_command,
        },
    )

    assert oversized_macro.status_code == 422
    assert oversized_template.status_code == 422
    assert oversized_plugin_caps.status_code == 422


def test_phase4_plugin_capabilities_require_domain_action_format() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4CapabilityFormat", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    invalid_caps = client.post(
        f"/api/sessions/{session_id}/plugins",
        json={
            "name": "BadCaps",
            "version": "1.0.0",
            "capabilities": ["macro:run", "invalidcap"],
            "command": host_command,
        },
    )
    assert invalid_caps.status_code == 422


def test_phase4_non_gm_cannot_list_automation_entities() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Phase4AutomationReadPolicy", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    macros = client.get(f"/api/sessions/{session_id}/macros", params={"actor_peer_id": "p1", "actor_token": p1_token})
    roll_templates = client.get(
        f"/api/sessions/{session_id}/roll-templates",
        params={"actor_peer_id": "p1", "actor_token": p1_token},
    )
    plugins = client.get(f"/api/sessions/{session_id}/plugins", params={"actor_peer_id": "p1", "actor_token": p1_token})

    assert macros.status_code == 403
    assert roll_templates.status_code == 403
    assert plugins.status_code == 403
