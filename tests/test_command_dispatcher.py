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
