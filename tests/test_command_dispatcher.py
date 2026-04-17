from app.commands.dispatcher import CommandDispatcher, InvalidCommandPayloadError, UnknownCommandError
from app.services.session_service import CommandContext, SessionService


def test_dispatcher_routes_move_token_command() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")

    result = dispatcher.dispatch(
        session_id=created['session_id'],
        action='move_token',
        payload={'token_id': 'hero', 'x': 2, 'y': 3},
        command=CommandContext(expected_revision=0),
    )

    assert result is not None
    assert result['map']['token_positions']['hero'] == (2, 3)
    assert result['revision'] == 1


def test_dispatcher_raises_for_unknown_command() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")

    try:
        dispatcher.dispatch(
            session_id=created['session_id'],
            action='does_not_exist',
            payload={},
            command=CommandContext(),
        )
    except UnknownCommandError:
        return
    assert False, "Expected UnknownCommandError for unregistered action"


def test_dispatcher_rejects_invalid_payload() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")

    try:
        dispatcher.dispatch(
            session_id=created['session_id'],
            action='move_token',
            payload={'token_id': '', 'x': -1, 'y': 0},
            command=CommandContext(expected_revision=0),
        )
    except InvalidCommandPayloadError:
        return
    assert False, "Expected InvalidCommandPayloadError for malformed command payload"


def test_dispatcher_roll_sheet_action_uses_server_formula_not_client_formula() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")
    session_id = created["session_id"]
    service.import_character(
        session_id=session_id,
        import_format="json_schema",
        payload='{"name":"Hero","character_class":"Fighter","level":3,"hit_points":24,"items":["Sword"]}',
        token_id="hero",
        command=CommandContext(actor_peer_id="dm"),
    )
    updated = dispatcher.dispatch(
        session_id=session_id,
        action="update_actor",
        payload={"actor_id": "hero", "skills": {"perception": {"modifier": 3, "proficiency": "expert"}}},
        command=CommandContext(actor_peer_id="dm", expected_revision=1),
    )
    assert updated is not None

    result = dispatcher.dispatch(
        session_id=session_id,
        action="roll_sheet_action",
        payload={
            "actor_id": "hero",
            "action_type": "skill",
            "action_key": "perception",
            "advantage_mode": "advantage",
            "visibility_mode": "public",
            "formula": "1d20+999",
        },
        command=CommandContext(actor_peer_id="dm", expected_revision=2),
    )
    assert result is not None
    assert result["formula"].startswith("2d20kh1")


def test_dispatcher_rejects_invalid_skill_proficiency_tier() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")

    try:
        dispatcher.dispatch(
            session_id=created['session_id'],
            action='update_actor',
            payload={
                'actor_id': 'hero',
                'skills': {'perception': {'modifier': 2, 'proficiency': 'legendary'}},
            },
            command=CommandContext(expected_revision=0),
        )
    except InvalidCommandPayloadError:
        return
    assert False, "Expected InvalidCommandPayloadError for unsupported proficiency tier"


def test_dispatcher_routes_scene_lighting_and_token_light_commands() -> None:
    service = SessionService()
    dispatcher = CommandDispatcher(service)
    created = service.create_session("Dispatch", "dm")
    session_id = created["session_id"]
    dispatcher.dispatch(
        session_id=session_id,
        action="move_token",
        payload={"token_id": "hero", "x": 2, "y": 3},
        command=CommandContext(expected_revision=0),
    )

    scene_result = dispatcher.dispatch(
        session_id=session_id,
        action="set_scene_lighting",
        payload={"preset": "night"},
        command=CommandContext(expected_revision=1),
    )
    assert scene_result is not None
    assert scene_result["map"]["scene_lighting_preset"] == "night"

    token_light_result = dispatcher.dispatch(
        session_id=session_id,
        action="set_token_light",
        payload={
            "token_id": "hero",
            "bright_radius": 4,
            "dim_radius": 8,
            "color": "#ffffff",
            "enabled": True,
        },
        command=CommandContext(expected_revision=2),
    )
    assert token_light_result is not None
    assert token_light_result["map"]["token_light_by_token"]["hero"]["enabled"] is True
