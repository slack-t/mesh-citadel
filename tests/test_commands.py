# tests/test_commands.py

import pytest

from citadel.commands.registry import registry
from citadel.commands import builtins
from citadel.commands.base import BaseCommand, CommandCategory
from citadel.auth.permissions import PermissionLevel


# -----------------------------------------------------------------------
# Registry
# -----------------------------------------------------------------------

@pytest.mark.parametrize("code,expected_class", [
    ("K", builtins.KnownRoomsCommand),
    ("G", builtins.ChangeRoomCommand),
    ("M", builtins.MailCommand),
    ("S", builtins.EnterMessageCommand),
    ("W", builtins.GoNextUnreadCommand),
    ("V", builtins.ForwardReadCommand),
    (".N", builtins.CreateRoomCommand),
    ("H", builtins.HelpCommand),
    ("B", builtins.BlockUserCommand),
])
def test_registry_lookup_returns_correct_class(code, expected_class):
    cls = registry.get(code)
    assert cls is expected_class
    assert issubclass(cls, BaseCommand)


def test_registry_get_unknown_code_returns_none():
    assert registry.get("NOPE") is None


def test_registry_available_is_a_copy():
    available = registry.available()
    available.clear()
    # Mutating the returned dict must not affect the registry.
    assert registry.available(), "registry.available() should return a copy"


def test_no_duplicate_command_codes():
    assert registry.get("S") is builtins.EnterMessageCommand
    assert registry.get("W") is builtins.GoNextUnreadCommand
    assert registry.get("V") is builtins.ForwardReadCommand
    assert registry.get("O") is builtins.WhoCommand
    assert registry.get("U") is builtins.ScanMessagesCommand
    assert registry.get("P") is builtins.ValidateUsersCommand


# -----------------------------------------------------------------------
# Command construction / serialization (args is a plain string now)
# -----------------------------------------------------------------------

def test_command_requires_username():
    with pytest.raises(ValueError):
        builtins.ChangeRoomCommand(username=None)


def test_command_to_dict_includes_username_and_room():
    cmd = builtins.EnterMessageCommand(
        username="alice", room="Lobby", args="hello world")
    d = cmd.to_dict()
    assert d["username"] == "alice"
    assert d["room"] == "Lobby"
    assert d["args"] == "hello world"
    assert d["code"] == "S"
    assert d["name"] == "enter_message"
    assert d["permission_level"] == PermissionLevel.USER.value


def test_default_args_is_empty_string():
    cmd = builtins.ChangeRoomCommand(username="alice")
    assert cmd.args == ""
    assert cmd.room is None


# -----------------------------------------------------------------------
# Metadata
# -----------------------------------------------------------------------

def test_permission_levels_are_set_correctly():
    assert builtins.CreateRoomCommand.permission_level == PermissionLevel.USER
    assert builtins.EditRoomCommand.permission_level == PermissionLevel.SYSOP
    assert builtins.FastForwardCommand.permission_level == PermissionLevel.USER


def test_help_and_short_text_present():
    cmd_cls = builtins.EnterMessageCommand
    assert cmd_cls.help_text.strip()
    assert cmd_cls.short_text.strip()


def test_validate_users_command_metadata():
    cmd_cls = builtins.ValidateUsersCommand
    assert cmd_cls.code == "P"
    assert cmd_cls.name == "validate_users"
    assert cmd_cls.permission_level == PermissionLevel.AIDE
    assert cmd_cls.category == CommandCategory.AIDE
    # German help text, but the stem "valid" survives translation.
    assert "valid" in cmd_cls.help_text.lower()


# -----------------------------------------------------------------------
# is_implemented reflects whether run() is overridden
# -----------------------------------------------------------------------

def test_is_implemented_distinguishes_stubs():
    # ChangeRoom has a real run(); IgnoreRoom is still a stub.
    assert builtins.ChangeRoomCommand.is_implemented() is True
    assert builtins.IgnoreRoomCommand.is_implemented() is False


# -----------------------------------------------------------------------
# What's left of validate(): EnterMessage still guards the Mail room.
# -----------------------------------------------------------------------

def test_enter_message_requires_recipient_in_mail_room():
    # Empty args in the Mail room means no recipient -> reject.
    cmd = builtins.EnterMessageCommand(
        username="alice", room="Mail", args="")
    with pytest.raises(ValueError):
        cmd.validate(context={"room": "Mail"})


def test_enter_message_ok_in_mail_room_with_recipient():
    cmd = builtins.EnterMessageCommand(
        username="alice", room="Mail", args="bob")
    cmd.validate(context={"room": "Mail"})  # should not raise


def test_enter_message_ok_in_regular_room():
    cmd = builtins.EnterMessageCommand(
        username="alice", room="Lobby", args="")
    cmd.validate(context={"room": "Lobby"})  # should not raise
