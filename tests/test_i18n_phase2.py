from types import SimpleNamespace

import pytest

from citadel.auth.permissions import PermissionLevel
from citadel.commands.base import CommandContext
from citadel.commands.builtins import GoNextUnreadCommand
from citadel.commands.processor import CommandProcessor
from citadel.i18n import resolve_locale
from citadel.room.room import Room, SystemRoomIDs
from citadel.session.manager import SessionManager
from citadel.session.state import SessionState
from citadel.transport.packets import FromUser, FromUserType, ToUser
from citadel.user.user import User
from citadel.workflows.base import WorkflowContext, WorkflowState


async def _make_user(db, config, username):
    await User.create(config, db, username, "hash", "salt", username)
    user = User(db, username)
    await user.load()
    await user.set_permission_level(PermissionLevel.USER)


def _login(session_mgr, username):
    session_id = session_mgr.create_session()
    session_mgr.mark_username(session_id, username)
    session_mgr.get_session_state(session_id).logged_in = True
    return session_id


def _packet(session_id, cmd):
    return FromUser(
        session_id=session_id,
        payload=cmd,
        payload_type=FromUserType.COMMAND,
    )


def test_resolve_locale_precedence():
    state = SessionState(locale="en")
    config = SimpleNamespace(system={"locale": "de"})

    assert resolve_locale(state, config) == "en"
    assert resolve_locale(SessionState(), config) == "de"
    assert resolve_locale(SessionState(), None) == "de"
    assert resolve_locale(None, None) == "de"


def test_command_context_t_uses_english_locale():
    ctx = CommandContext(
        db=None,
        config=None,
        session_mgr=None,
        msg_mgr=None,
        session_id="sid",
        locale="en",
    )

    assert ctx.t("room.enter", room="Lobby") == "Welcome to the 'Lobby' room."


def test_command_context_t_uses_german_locale():
    ctx = CommandContext(
        db=None,
        config=None,
        session_mgr=None,
        msg_mgr=None,
        session_id="sid",
        locale="de",
    )

    assert ctx.t("room.enter", room="Lobby") == "Willkommen im Raum 'Lobby'."


def test_workflow_context_t_uses_session_locale():
    ctx = WorkflowContext(
        session_id="sid",
        db=None,
        config=None,
        session_mgr=None,
        wf_state=WorkflowState(kind="login"),
        locale="en",
    )

    assert ctx.t("room.enter", room="Lobby") == "Welcome to the 'Lobby' room."


def test_context_t_missing_key_fails_soft():
    ctx = CommandContext(
        db=None,
        config=None,
        session_mgr=None,
        msg_mgr=None,
        session_id="sid",
        locale="en",
    )

    assert ctx.t("nonexistent.key") == "nonexistent.key"


@pytest.mark.asyncio
async def test_processor_uses_session_locale_for_go_next_unread(db, config):
    session_mgr = SessionManager(config, db)
    await _make_user(db, config, "alice")
    session_id = _login(session_mgr, "alice")
    session_mgr.get_session_state(session_id).locale = "en"

    new_room_id = await Room.create(
        db,
        config,
        "General",
        "",
        False,
        PermissionLevel.USER,
        SystemRoomIDs.LOBBY_ID,
        "alice",
    )
    general = Room(db, config, new_room_id)
    await general.load()
    await general.post_message("alice", "hello world")

    processor = CommandProcessor(config, db, session_mgr)
    resp = await processor.process(
        _packet(session_id, GoNextUnreadCommand(username="alice"))
    )

    assert isinstance(resp, ToUser)
    assert "Welcome to" in resp.text
    assert "Willkommen" not in resp.text


def test_resolve_locale_empty_string_falls_through():
    state = SessionState(locale="")
    config = SimpleNamespace(system={"locale": "en"})

    assert resolve_locale(state, config) == "en"


def test_resolve_locale_reads_from_config():
    config = SimpleNamespace(system={"locale": "en"})

    assert resolve_locale(SessionState(), config) == "en"
    assert resolve_locale(None, config) == "en"
