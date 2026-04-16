import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from net.signaling_service import app


def test_session_websocket_receives_event() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "WS", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    with client.websocket_connect(f"/api/sessions/{session_id}/events?actor_peer_id=dm&actor_token={host_token}") as ws:
        ws.send_text('subscribe')
        moved = client.post(
            f'/api/sessions/{session_id}/move-token',
            json={"token_id": "hero", "x": 1, "y": 1},
        )
        assert moved.status_code == 200
        event = json.loads(ws.receive_text())
        assert event['event_id']
        assert event['event_type'] == 'token_moved'
        assert event['revision'] == 1
        assert event['payload']['token_id'] == 'hero'


def test_event_replay_returns_events_after_revision() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "Replay", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    first_move = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 1, "y": 1},
    )
    second_move = client.post(
        f'/api/sessions/{session_id}/move-token',
        json={"token_id": "hero", "x": 2, "y": 2, "command": {"expected_revision": 1}},
    )
    assert first_move.status_code == 200
    assert second_move.status_code == 200

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 1, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    events = replay.json()['events']
    assert len(events) >= 1
    assert any(event['revision'] == 2 for event in events)


def test_duplicate_idempotent_map_command_emits_single_event() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ReplayIdempotency", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    first = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={
            "x": 4,
            "y": 5,
            "terrain_type": "forest",
            "command": {"expected_revision": 0, "idempotency_key": "terrain-op"},
        },
    )
    assert first.status_code == 200
    assert first.json()['state']['revision'] == 1

    duplicate = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={
            "x": 1,
            "y": 1,
            "terrain_type": "water",
            "command": {"expected_revision": 1, "idempotency_key": "terrain-op"},
        },
    )
    assert duplicate.status_code == 200
    assert duplicate.json()['state']['revision'] == 1
    assert duplicate.json()['state']['map']['terrain_tiles']['4:5'] == 'forest'

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    terrain_events = [event for event in replay.json()['events'] if event.get('event_type') == 'terrain_painted']
    assert len(terrain_events) == 1


def test_conflicting_combat_commands_return_409_and_single_event() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "CombatRace", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    first = client.post(
        f'/api/sessions/{session_id}/initiative',
        json={"order": ["hero"], "command": {"expected_revision": 0, "idempotency_key": "init-1"}},
    )
    assert first.status_code == 200
    assert first.json()['state']['revision'] == 1

    stale = client.post(
        f'/api/sessions/{session_id}/initiative',
        json={"order": ["hero", "goblin"], "command": {"expected_revision": 0, "idempotency_key": "init-2"}},
    )
    assert stale.status_code == 409

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    combat_events = [event for event in replay.json()['events'] if event.get('event_type') == 'initiative_set']
    assert len(combat_events) == 1
    assert combat_events[0]['revision'] == 1


def test_websocket_subscription_rejects_missing_session() -> None:
    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect('/api/sessions/not-found/events?actor_peer_id=dm&actor_token=missing') as ws:
            ws.send_text('subscribe')
            ws.receive_text()


def test_unknown_peer_cannot_escalate_websocket_context_with_actor_role_claim() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "WsRoleSpoof", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/api/sessions/{session_id}/events?actor_peer_id=intruder&actor_role=GM') as ws:
            ws.send_text('subscribe')
            ws.receive_text()


def test_mixed_command_replay_sequence_has_monotonic_unique_revisions() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "MixedReplay", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    actor_update = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 10, "command": {"expected_revision": 0, "idempotency_key": "actor-1"}},
    )
    assert actor_update.status_code == 200
    assert actor_update.json()['state']['revision'] == 1

    duplicate_actor_update = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 9, "command": {"expected_revision": 1, "idempotency_key": "actor-1"}},
    )
    assert duplicate_actor_update.status_code == 200
    assert duplicate_actor_update.json()['state']['revision'] == 1

    map_update = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={"x": 6, "y": 6, "terrain_type": "stone", "command": {"expected_revision": 1, "idempotency_key": "map-1"}},
    )
    assert map_update.status_code == 200
    assert map_update.json()['state']['revision'] == 2

    stale_map_update = client.post(
        f'/api/sessions/{session_id}/paint-terrain',
        json={"x": 1, "y": 1, "terrain_type": "water", "command": {"expected_revision": 1, "idempotency_key": "map-stale"}},
    )
    assert stale_map_update.status_code == 409

    combat_update = client.post(
        f'/api/sessions/{session_id}/initiative',
        json={"order": ["hero"], "command": {"expected_revision": 2, "idempotency_key": "combat-1"}},
    )
    assert combat_update.status_code == 200
    assert combat_update.json()['state']['revision'] == 3

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    events = replay.json()['events']
    revisions = [event['revision'] for event in events if isinstance(event.get('revision'), int)]
    assert revisions == sorted(revisions)
    assert len(revisions) == len(set(revisions))
    assert revisions[-1] == 3


def test_player_replay_redacts_unowned_actor_events() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ReplayVisibility", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join.status_code == 200
    p1_token = join.json()['peer_token']

    hero = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "hero", "hit_points": 10, "command": {"expected_revision": 0}},
    )
    goblin = client.post(
        f'/api/sessions/{session_id}/actor-state',
        json={"actor_id": "goblin", "hit_points": 7, "command": {"expected_revision": 1}},
    )
    assert hero.status_code == 200
    assert goblin.status_code == 200

    assign_owner = client.post(
        f'/api/sessions/{session_id}/actor-ownership',
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
    )
    assert assign_owner.status_code == 200

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "p1", "actor_token": p1_token},
    )
    assert replay.status_code == 200
    actor_events = [event for event in replay.json()['events'] if event.get('event_type') == 'actor_updated']
    assert len(actor_events) == 2
    payloads = [event['payload'] for event in actor_events]
    assert {'actor_id': 'hero'} in payloads
    assert {} in payloads


def test_player_websocket_redacts_unowned_actor_events() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "WsVisibility", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert join.status_code == 200
    p1_token = join.json()['peer_token']

    with client.websocket_connect(f"/api/sessions/{session_id}/events?actor_peer_id=p1&actor_token={p1_token}") as ws:
        ws.send_text('subscribe')
        create_hero = client.post(
            f'/api/sessions/{session_id}/actor-state',
            json={"actor_id": "hero", "hit_points": 10, "command": {"expected_revision": 0}},
        )
        create_goblin = client.post(
            f'/api/sessions/{session_id}/actor-state',
            json={"actor_id": "goblin", "hit_points": 7, "command": {"expected_revision": 1}},
        )
        assign_owner = client.post(
            f'/api/sessions/{session_id}/actor-ownership',
            json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 2}},
        )
        update_hero = client.post(
            f'/api/sessions/{session_id}/actor-state',
            json={"actor_id": "hero", "hit_points": 9, "command": {"expected_revision": 3}},
        )
        update_goblin = client.post(
            f'/api/sessions/{session_id}/actor-state',
            json={"actor_id": "goblin", "hit_points": 6, "command": {"expected_revision": 4}},
        )
        assert create_hero.status_code == 200
        assert create_goblin.status_code == 200
        assert assign_owner.status_code == 200
        assert update_hero.status_code == 200
        assert update_goblin.status_code == 200

        event_payloads = [json.loads(ws.receive_text()).get('payload', {}) for _ in range(5)]
        assert {'actor_id': 'hero'} in event_payloads
        assert {} in event_payloads


def test_non_gm_websocket_redacts_phase4_automation_events() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "WsPhase4Redaction", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']
    host_command = {"actor_peer_id": "dm", "actor_token": host_token}

    joined = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    assert joined.status_code == 200
    p1_token = joined.json()['peer_token']

    with client.websocket_connect(f"/api/sessions/{session_id}/events?actor_peer_id=p1&actor_token={p1_token}") as ws:
        ws.send_text('subscribe')
        created_macro = client.post(
            f"/api/sessions/{session_id}/macros",
            json={"name": "Cast", "template": "{actor} casts {spell}.", "command": host_command},
        )
        assert created_macro.status_code == 200
        macro_id = created_macro.json()['macro']['macro_id']

        ran_macro = client.post(
            f"/api/sessions/{session_id}/macros/{macro_id}/run",
            json={"variables": {"actor": "Nyx", "spell": "Shield"}, "command": host_command},
        )
        assert ran_macro.status_code == 200

        registered_plugin = client.post(
            f"/api/sessions/{session_id}/plugins",
            json={"name": "Hooks", "version": "1.0.0", "capabilities": ["macro:run"], "command": host_command},
        )
        assert registered_plugin.status_code == 200
        plugin_id = registered_plugin.json()['plugin']['plugin_id']

        hook_failed = client.post(
            f"/api/sessions/{session_id}/plugins/{plugin_id}/hooks/after_event/execute",
            json={"payload": {"event_type": "macro_ran", "simulate_failure": True}, "command": host_command},
        )
        assert hook_failed.status_code == 200

        observed = [json.loads(ws.receive_text()) for _ in range(4)]
        for event in observed:
            assert event['event_type'] in {'macro_created', 'macro_ran', 'plugin_registered', 'plugin_hook_failed'}
            assert event['payload'] == {}


def test_visibility_recompute_emits_ws_event_and_replays_by_revision() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "VisionWS", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    move = client.post(f'/api/sessions/{session_id}/move-token', json={"token_id": "hero", "x": 1, "y": 1})
    block = client.post(
        f'/api/sessions/{session_id}/toggle-blocked',
        json={"x": 2, "y": 1, "command": {"expected_revision": 1}},
    )
    assert move.status_code == 200
    assert block.status_code == 200

    with client.websocket_connect(f"/api/sessions/{session_id}/events?actor_peer_id=dm&actor_token={host_token}") as ws:
        ws.send_text('subscribe')
        recompute = client.post(
            f'/api/sessions/{session_id}/recompute-visibility',
            json={"token_id": "hero", "radius": 3, "command": {"expected_revision": 2, "idempotency_key": "vision-evt-1"}},
        )
        assert recompute.status_code == 200
        event = json.loads(ws.receive_text())
        assert event['event_type'] == 'vision_updated'
        assert event['revision'] == 3
        assert event['payload']['token_id'] == 'hero'

    duplicate = client.post(
        f'/api/sessions/{session_id}/recompute-visibility',
        json={"token_id": "hero", "radius": 1, "command": {"expected_revision": 3, "idempotency_key": "vision-evt-1"}},
    )
    assert duplicate.status_code == 200
    assert duplicate.json()['state']['revision'] == 3

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 2, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    vision_events = [event for event in replay.json()['events'] if event.get('event_type') == 'vision_updated']
    assert len(vision_events) == 1
    assert vision_events[0]['revision'] == 3


def test_visibility_events_are_filtered_by_token_ownership() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "VisionOwnershipEvents", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    join_p1 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p1"})
    join_p2 = client.post(f"/api/sessions/{session_id}/join", json={"peer_id": "p2"})
    assert join_p1.status_code == 200
    assert join_p2.status_code == 200
    p1_token = join_p1.json()['peer_token']
    p2_token = join_p2.json()['peer_token']

    hero = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 2, "y": 2})
    assert hero.status_code == 200
    owner = client.post(
        f"/api/sessions/{session_id}/actor-ownership",
        json={"actor_id": "hero", "peer_id": "p1", "command": {"expected_revision": 1}},
    )
    assert owner.status_code == 200

    with client.websocket_connect(f"/api/sessions/{session_id}/events?actor_peer_id=p1&actor_token={p1_token}") as ws1, client.websocket_connect(
        f"/api/sessions/{session_id}/events?actor_peer_id=p2&actor_token={p2_token}"
    ) as ws2:
        ws1.send_text('subscribe')
        ws2.send_text('subscribe')
        recompute = client.post(
            f"/api/sessions/{session_id}/recompute-visibility",
            json={"token_id": "hero", "radius": 3, "command": {"expected_revision": 2}},
        )
        assert recompute.status_code == 200
        e1 = json.loads(ws1.receive_text())
        e2 = json.loads(ws2.receive_text())
        assert e1['event_type'] == 'vision_updated'
        assert e2['event_type'] == 'vision_updated'
        assert e1['payload'].get('token_id') == 'hero'
        assert e2['payload'] == {}

    replay_p1 = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 2, "actor_peer_id": "p1", "actor_token": p1_token},
    )
    replay_p2 = client.get(
        f"/api/sessions/{session_id}/events/replay",
        params={"after_revision": 2, "actor_peer_id": "p2", "actor_token": p2_token},
    )
    assert replay_p1.status_code == 200
    assert replay_p2.status_code == 200
    p1_event = next(event for event in replay_p1.json()['events'] if event.get('event_type') == 'vision_updated')
    p2_event = next(event for event in replay_p2.json()['events'] if event.get('event_type') == 'vision_updated')
    assert p1_event['payload'].get('token_id') == 'hero'
    assert p2_event['payload'] == {}


def test_token_vision_updates_emit_single_event_on_idempotent_replay() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "TokenVisionReplay", "host_peer_id": "dm"})
    session_id = created.json()['session_id']
    host_token = created.json()['host_peer_token']

    moved = client.post(f"/api/sessions/{session_id}/move-token", json={"token_id": "hero", "x": 1, "y": 1})
    assert moved.status_code == 200

    first = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "hero", "radius": 5, "command": {"expected_revision": 1, "idempotency_key": "vision-radius-1"}},
    )
    duplicate = client.post(
        f"/api/sessions/{session_id}/token-vision",
        json={"token_id": "hero", "radius": 2, "command": {"expected_revision": 2, "idempotency_key": "vision-radius-1"}},
    )
    assert first.status_code == 200
    assert duplicate.status_code == 200
    assert first.json()['state']['revision'] == 2
    assert duplicate.json()['state']['revision'] == 2
    assert duplicate.json()['state']['map']['vision_radius_by_token']['hero'] == 5

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": host_token},
    )
    assert replay.status_code == 200
    vision_events = [event for event in replay.json()['events'] if event.get('event_type') == 'token_vision_updated']
    assert len(vision_events) == 1


def test_event_replay_requires_actor_peer_id() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ReplayAuth", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    replay = client.get(f'/api/sessions/{session_id}/events/replay', params={"after_revision": 0})
    assert replay.status_code == 403


def test_event_replay_requires_valid_actor_token() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "ReplayTokenAuth", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    replay = client.get(
        f'/api/sessions/{session_id}/events/replay',
        params={"after_revision": 0, "actor_peer_id": "dm", "actor_token": "invalid"},
    )
    assert replay.status_code == 403


def test_websocket_subscription_requires_actor_peer_id() -> None:
    client = TestClient(app)
    created = client.post('/api/sessions', json={"session_name": "WsAuth", "host_peer_id": "dm"})
    session_id = created.json()['session_id']

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f'/api/sessions/{session_id}/events') as ws:
            ws.send_text('subscribe')
            ws.receive_text()
