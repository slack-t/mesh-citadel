# tests/test_dot_commands.py

from citadel.commands import builtins
from citadel.commands.base import CommandCategory
from citadel.auth.permissions import PermissionLevel


# The old per-command arg_schema validation system has been retired:
# validate() is now a permissive no-op (commands check their own args inside
# run()), and the dot-command codes were renamed. These tests pin down the
# current metadata and implementation status instead.


def test_dot_command_codes():
    assert builtins.CreateRoomCommand.code == ".N"
    assert builtins.EditRoomCommand.code == ".RR"
    assert builtins.EditUserCommand.code == ".UB"
    assert builtins.FastForwardCommand.code == ".S"
    assert builtins.KillRoomCommand.code == ".KR"


def test_permissions_for_dot_commands():
    assert builtins.CreateRoomCommand.permission_level == PermissionLevel.USER
    assert builtins.EditRoomCommand.permission_level == PermissionLevel.SYSOP
    assert builtins.EditUserCommand.permission_level == PermissionLevel.SYSOP
    assert builtins.FastForwardCommand.permission_level == PermissionLevel.USER
    assert builtins.KillRoomCommand.permission_level == PermissionLevel.SYSOP


def test_dot_command_categories():
    assert builtins.CreateRoomCommand.category == CommandCategory.UNUSUAL
    assert builtins.EditRoomCommand.category == CommandCategory.SYSOP
    assert builtins.EditUserCommand.category == CommandCategory.SYSOP
    assert builtins.KillRoomCommand.category == CommandCategory.SYSOP


def test_implemented_dot_commands():
    # CreateRoom and KillRoom have real run() methods; the editors are stubs.
    assert builtins.CreateRoomCommand.is_implemented() is True
    assert builtins.KillRoomCommand.is_implemented() is True
    assert builtins.EditRoomCommand.is_implemented() is False
    assert builtins.EditUserCommand.is_implemented() is False
    assert builtins.FastForwardCommand.is_implemented() is False


def test_validate_is_permissive_noop():
    # validate() no longer enforces an argument schema for these commands.
    builtins.CreateRoomCommand(username="aide", args="").validate(context={})
    builtins.EditRoomCommand(username="sysop", args="").validate(context={})
    builtins.EditUserCommand(username="sysop", args="").validate(context={})
    builtins.FastForwardCommand(username="bob", args="").validate(context={})
