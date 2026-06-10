import pytest

from citadel.auth.permissions import PermissionLevel
from citadel.commands.processor import CommandProcessor
from citadel.commands.builtins import (
    GoNextUnreadCommand,
    ChangeRoomCommand,
    EnterMessageCommand,
    ReadNewMessagesCommand,
)
from citadel.room.room import Room, SystemRoomIDs
from citadel.session.manager import SessionManager
from citadel.transport.packets import ToUser, FromUser, FromUserType
from citadel.user.user import User

# `config` and `db` come from tests/conftest.py.


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
    return FromUser(session_id=session_id, payload=cmd,
                    payload_type=FromUserType.COMMAND)


@pytest.mark.asyncio
async def test_go_next_unread_moves_session(db, config):
    session_mgr = SessionManager(config, db)
    await _make_user(db, config, "alice")
    session_id = _login(session_mgr, "alice")

    new_room_id = await Room.create(
        db, config, 'General', '', False, PermissionLevel.USER,
        SystemRoomIDs.LOBBY_ID, "alice")
    general = Room(db, config, new_room_id)
    await general.load()
    await general.post_message("alice", "hello world")

    processor = CommandProcessor(config, db, session_mgr)
    resp = await processor.process(_packet(session_id, GoNextUnreadCommand(username="alice")))

    assert isinstance(resp, ToUser)
    assert session_mgr.get_current_room(session_id) == new_room_id


@pytest.mark.asyncio
async def test_change_room_by_name_and_id(db, config):
    session_mgr = SessionManager(config, db)
    await _make_user(db, config, "bob")
    session_id = _login(session_mgr, "bob")

    room_id = await Room.create(db, config, 'TechTalk', '', False,
                                PermissionLevel.USER, SystemRoomIDs.LOBBY_ID, "bob")

    processor = CommandProcessor(config, db, session_mgr)

    # Change by name (args is a plain string now).
    resp = await processor.process(_packet(session_id, ChangeRoomCommand(username="bob", args="TechTalk")))
    assert isinstance(resp, ToUser)
    assert not resp.is_error, f'got an error: {resp.error_code}'
    assert session_mgr.get_current_room(session_id) == room_id

    # Change by id.
    resp = await processor.process(_packet(session_id, ChangeRoomCommand(username="bob", args=str(room_id))))
    assert isinstance(resp, ToUser)
    assert session_mgr.get_current_room(session_id) == room_id


@pytest.mark.asyncio
async def test_enter_message_in_mail_room_prompts_for_recipient(db, config):
    session_mgr = SessionManager(config, db)
    await _make_user(db, config, "carol")
    session_id = _login(session_mgr, "carol")
    session_mgr.set_current_room(session_id, SystemRoomIDs.MAIL_ID)

    processor = CommandProcessor(config, db, session_mgr)
    resp = await processor.process(_packet(session_id, EnterMessageCommand(username="carol")))

    # In the Mail room the enter_message workflow starts by asking for a
    # recipient (step 1) rather than erroring.
    assert isinstance(resp, ToUser)
    assert not resp.is_error
    wf = session_mgr.get_workflow(session_id)
    assert wf is not None and wf.kind == "enter_message"
    assert wf.step == 1


@pytest.mark.asyncio
async def test_read_new_messages_returns_unread(db, config):
    session_mgr = SessionManager(config, db)
    await _make_user(db, config, "erin")
    session_id = _login(session_mgr, "erin")

    room_id = await Room.create(db, config, 'General', '', False,
                                PermissionLevel.USER, SystemRoomIDs.LOBBY_ID, "erin")
    session_mgr.set_current_room(session_id, room_id)

    room = Room(db, config, room_id)
    await room.load()
    await room.post_message("erin", "first")
    await room.post_message("erin", "second")

    processor = CommandProcessor(config, db, session_mgr)
    resp = await processor.process(_packet(session_id, ReadNewMessagesCommand(username="erin")))

    assert isinstance(resp, list)
    assert all(isinstance(r, ToUser) for r in resp)
    assert len(resp) == 2
    assert resp[0].message.content == "first"
    assert resp[1].message.content == "second"
