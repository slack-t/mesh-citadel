# bbs/commands/builtins.py

from datetime import datetime, UTC
import logging

from citadel.commands.base import BaseCommand, CommandCategory
from citadel.commands.registry import register_command
from citadel.auth.permissions import PermissionLevel
from citadel.commands.responses import MessageResponse
from citadel.transport.packets import ToUser
from citadel.auth.permissions import is_allowed
from citadel.room.room import Room, SystemRoomIDs, RoomNotFoundError
from citadel.user.user import User
from citadel.workflows.base import WorkflowContext, WorkflowState

log = logging.getLogger(__name__)

# -------------------
# Core user commands
# -------------------

# command categories:
# * common
# * uncommon
# * unusual
# * admin


async def scan_messages(context, msg_ids):
    """given a set of message IDs, return a list of ToUser objects,
    each containing one of the indicated messages"""
    state = context.session_mgr.get_session_state(context.session_id)
    user = User(context.db, state.username)
    await user.load()
    room = Room(context.db, context.config, state.current_room)
    await room.load()
    if not msg_ids:
        return ToUser(
            session_id=context.session_id,
            text="Gähn... absolut tote Hose (Keine Nachrichten)"
        )

    msgs = []
    for msg_id in msg_ids:
        msg = await context.msg_mgr.get_message_summary(
            msg_id,
            recipient_user=user,
            msg_len=50
        )
        # Message not authorized for this user (privacy check failed)
        if not msg:
            continue

        msgs.append(msg)

    return ToUser(
        session_id=context.session_id,
        text='\n'.join(msgs)
    )


async def read_messages(context, msg_ids):
    """given a set of message IDs, return a list of ToUser objects,
    each containing one of the indicated messages"""
    state = context.session_mgr.get_session_state(context.session_id)
    user = User(context.db, state.username)
    await user.load()
    room = Room(context.db, context.config, state.current_room)
    await room.load()
    if not msg_ids:
        return ToUser(
            session_id=context.session_id,
            text="Nix Neues hier, Digger."
        )

    to_user_list = []
    for msg_id in msg_ids:
        msg = await context.msg_mgr.get_message(msg_id, recipient_user=user)
        # Message not authorized for this user (privacy check failed)
        if not msg:
            continue
        sender = User(context.db, msg["sender"])
        await sender.load()
        message_response = MessageResponse(
            id=msg["id"],
            sender=msg["sender"],
            display_name=sender.display_name,
            timestamp=msg["timestamp"],
            room=room.name,
            content=msg["content"],
            blocked=msg["blocked"],
            recipient=msg["recipient"]
        )
        log.debug(f"Adding message to read list: {msg['id']}")
        to_user_list.append(ToUser(
            session_id=context.session_id,
            text="",  # Message content is in the message field
            message=message_response
        ))

    # Mark all displayed messages as read by advancing to latest
    await room.skip_to_latest(user)
    log.debug(f"Returning list of {len(to_user_list)} messages")
    return to_user_list


@register_command
class GoNextUnreadCommand(BaseCommand):
    code = "O"
    name = "go_next_unread"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nächster Raum mit neuen Nachrichten"
    help_text = "Gehe zum nächsten Raum mit ungelesenen Nachrichten. Überspringt Räume, die du schon kennst."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        room = Room(context.db, context.config, state.current_room)
        await room.load()
        new_room = await room.go_to_next_room(user, with_unread=True)
        await new_room.load()
        context.session_mgr.set_current_room(
            context.session_id, new_room.room_id)

        # Check if we wrapped to Lobby due to no unread rooms
        if new_room.room_id == SystemRoomIDs.LOBBY_ID and room.room_id != SystemRoomIDs.LOBBY_ID:
            # Check if there are any unread messages in the system

            # TODO: this only checks if *lobby* has new messages, not
            # all rooms in the system. update to check every room.
            lobby_has_unread = await new_room.has_unread_messages(user)
            if lobby_has_unread:
                return ToUser(
                    session_id=context.session_id,
                    text=f"Willkommen im Raum '{new_room.name}'. New messages are available in other rooms."
                )
            else:
                return ToUser(
                    session_id=context.session_id,
                    text=f"Willkommen im Raum '{new_room.name}'. No rooms with unread messages found."
                )

        return ToUser(
            session_id=context.session_id,
            text=f"Willkommen im Raum '{new_room.name}'."
        )


@register_command
class EnterMessageCommand(BaseCommand):
    code = "U"
    name = "enter_message"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachricht schreiben"
    help_text = "Verfass eine neue Nachricht in diesem Raum."

    def validate(self, context=None):
        super().validate(context)
        if context and context.get("room") == "Mail" and not self.args:
            raise ValueError("Recipient required in Mail room")

    async def run(self, context):
        from citadel.workflows.registry import get as get_workflow

        state = context.session_mgr.get_session_state(context.session_id)
        if not state:
            return ToUser(
                session_id=context.session_id,
                text="Session nicht gefunden",
                is_error=True,
                error_code="no_session"
            )

        wf_state = WorkflowState(kind="enter_message", step=1, data={})
        # Start the workflow
        context.session_mgr.set_workflow(context.session_id, wf_state)
        wf_context = WorkflowContext(
            session_id=context.session_id,
            db=context.db,
            config=context.config,
            session_mgr=context.session_mgr,
            wf_state=wf_state
        )

        workflow = get_workflow("enter_message")
        return await workflow.start(wf_context)


@register_command
class ReverseReadCommand(BaseCommand):
    code = "R"
    name = "reverse_read"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachrichten rückwärts lesen"
    help_text = "Lies Nachrichten von neu nach alt."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        room = Room(context.db, context.config, state.current_room)
        await room.load()
        msg_ids = await room.get_user_message_ids(user, reverse=True)
        log.debug(f"Found reverse message ids: {msg_ids}")
        return await read_messages(context, msg_ids)


@register_command
class ForwardReadCommand(BaseCommand):
    code = "P"
    name = "forward_read"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachrichten vorwärts lesen"
    help_text = "Lies Nachrichten von alt nach neu."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        room = Room(context.db, context.config, state.current_room)
        await room.load()
        msg_ids = await room.get_user_message_ids(user)
        log.debug(f"Found forward message ids: {msg_ids}")
        return await read_messages(context, msg_ids)


@register_command
class ReadNewMessagesCommand(BaseCommand):
    code = "N"
    name = "read_new_messages"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Neue Nachrichten lesen"
    help_text = "Lies nur Nachrichten, die du noch nicht gesehen hast."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        room = Room(context.db, context.config, state.current_room)
        await room.load()
        msg_ids = await room.get_unread_message_ids(state.username)
        log.debug(f"Found new message ids: {msg_ids}")
        return await read_messages(context, msg_ids)


@register_command
class KnownRoomsCommand(BaseCommand):
    code = "K"
    name = "known_rooms"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Bekannte Räume"
    help_text = "Zeigt alle Räume, die du kennst."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()

        current_room_id = state.current_room

        rooms = await Room.get_all_visible_rooms(
            context.db, context.config, user
        )

        if not rooms:
            return ToUser(
                session_id=context.session_id,
                text="Sorry, für dich gibt's hier keine Räume."
            )

        lines = []
        for room in rooms:
            pre_marker = "-"
            post_marker = ""

            if room.room_id == current_room_id:
                post_marker = "<--"

            unread = await room.has_unread_messages(user)
            if unread:
                pre_marker = "*"

            line = f"{pre_marker} {room.name} {post_marker}"
            lines.append(line)

        room_list = "\n".join(lines)
        return ToUser(
            session_id=context.session_id,
            text=f"Hier sind unsere Räume:\n\n{room_list}"
        )


@register_command
class IgnoreRoomCommand(BaseCommand):
    code = "I"
    name = "ignore_room"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Raum ignorieren"
    help_text = "Ignoriere den aktuellen Raum oder hebe die Ignorierung auf."


@register_command
class QuitCommand(BaseCommand):
    code = "T"
    name = "quit"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Abhauen (Quit)"
    help_text = "Ausloggen und tschüss."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        old_username = state.username if state else "unknown"

        log.info(f"User '{old_username}' logged out via quit command")

        # Start login workflow on existing session (resets to anonymous state)
        session_id, login_prompt = await context.session_mgr.start_login_workflow(
            context.config, context.db, context.session_id
        )

        if login_prompt:
            login_prompt.text = "Hau rein!\n\n" + login_prompt.text
            return login_prompt
        else:
            # Fallback if login workflow unavailable
            return ToUser(
                session_id=state.session_id,
                text="Tschüssikowski! Komm wieder wenn du eingeloggt bist."
            )


@register_command
class StopCommand(BaseCommand):
    code = "STOPP"  # Use full word since this is a special case
    name = "stop"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachrichten stoppen"
    help_text = "Hört auf, Nachrichten zu spammen."

    async def run(self, context):
        num = await context.session_mgr.clear_msg_queue(context.session_id)
        if num == 1:
            mword = "message"
        else:
            mword = "messages"
        return ToUser(
            session_id=context.session_id,
            text=f"Notbremse gezogen: {num} pending {mword}"
        )


@register_command
class CancelCommand(BaseCommand):
    code = "ABBRUCH"  # Use full word since this is a special case
    name = "cancel"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Aktion abbrechen"
    help_text = "Bricht den aktuellen Workflow ab und geht zurück in den Normalmodus."

    async def run(self, context):
        from citadel.workflows import registry as workflow_registry

        # Check if user is in a workflow
        workflow_state = context.session_mgr.get_workflow(context.session_id)
        if not workflow_state:
            return ToUser(
                session_id=context.session_id,
                text="Gibt nix abzubrechen, chill.",
                is_error=True,
                error_code="no_workflow"
            )

        # Call cleanup on the workflow if it has one
        handler = workflow_registry.get(workflow_state.kind)
        if handler and hasattr(handler, 'cleanup'):
            try:
                await handler.cleanup(context)
            except Exception as e:
                log.warning(
                    f"Error during workflow cleanup for {workflow_state.kind}: {e}")

        # Clear the workflow
        context.session_mgr.clear_workflow(context.session_id)

        # If the user is not logged in (e.g., cancelling registration/login), start login workflow
        session_state = context.session_mgr.get_session_state(
            context.session_id)
        if not session_state or not context.session_mgr.is_logged_in(context.session_id):
            session_id, login_prompt = await context.session_mgr.start_login_workflow(
                context.config, context.db, context.session_id
            )
            if login_prompt:
                login_prompt.text = f"Eiskalt abgebrochen: {workflow_state.kind} workflow.\n\n" + \
                    login_prompt.text
                return login_prompt

        return ToUser(
            session_id=context.session_id,
            text=f"Eiskalt abgebrochen: {workflow_state.kind} workflow."
        )


@register_command
class ScanMessagesCommand(BaseCommand):
    code = "U"
    name = "scan_messages"
    category = CommandCategory.UNCOMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachrichten überfliegen"
    help_text = "Zeigt eine Zusammenfassung der Nachrichten in diesem Raum."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        room = Room(context.db, context.config, state.current_room)
        await room.load()
        msg_ids = await room.get_user_message_ids(user)
        return await scan_messages(context, msg_ids)


@register_command
class ChangeRoomCommand(BaseCommand):
    code = "G"
    name = "change_room"
    category = CommandCategory.UNCOMMON
    permission_level = PermissionLevel.USER
    short_text = "Raum wechseln"
    help_text = "Wechsle in einen anderen Raum. Gib den Namen oder die Nummer nach dem Kommando ein."
    # add an args attribute for any command that takes an argument
    args = ""

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        current_room = Room(context.db, context.config, state.current_room)
        await current_room.load()
        try:
            next_room = await current_room.go_to_room(self.args)
            await next_room.load()
            log.debug(f'preparing to go to room {self.args}')
        except RoomNotFoundError:
            return ToUser(
                session_id=context.session_id,
                text=f"Raum {self.args} nicht gefunden.",
                is_error=True,
                error_code="no_next_room"
            )
        context.session_mgr.set_current_room(
            context.session_id, next_room.room_id)
        return ToUser(
            session_id=context.session_id,
            text=f"Willkommen im Raum '{next_room.name}'."
        )


@register_command
class HelpCommand(BaseCommand):
    code = "H"
    name = "help"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Hilfe"
    help_text = "Zeigt das Hilfemenü mit allen Kommandos."

    async def run(self, context):
        from citadel.commands.registry import registry

        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()

        # Get current room for permission checking
        room = None
        if state.current_room:
            room = Room(context.db, context.config, state.current_room)
            await room.load()

        # If specific command requested, show detailed help
        if "command" in self.args and self.args["command"]:
            return await self._show_command_help(context.session_id, self.args["command"], user, room)

        # Build dynamic menu by category
        all_commands = registry.available()
        menus = []
        for category in CommandCategory:
            text = self._build_category_menu(
                all_commands, user, room, category)
            if 'No available' in text:
                continue
            menus.append(text)

        return ToUser(
            session_id=context.session_id,
            text="\n\n".join(menus)
        )

    def _build_category_menu(self, all_commands, user, room, category):
        """Build menu for a specific category."""
        # Filter to implemented commands user can access in this category
        available_commands = []
        for cmd_class in all_commands.values():
            if (cmd_class.is_implemented() and
                cmd_class.category == category and
                    is_allowed(cmd_class.name, user, room)):
                available_commands.append(cmd_class)

        # Sort by command code for consistent ordering
        available_commands.sort(key=lambda c: c.code)

        # Build compact menu text
        menu_lines = []
        for cmd in available_commands:
            menu_lines.append(f"{cmd.code}-{cmd.short_text}")

        if not menu_lines:
            return "Keine verfügbaren Kommandos in dieser Kategorie."

        # Add category header and join lines
        category_map = {
            "Common": "Standard",
            "Uncommon": "Fortgeschritten",
            "Unusual": "Selten",
            "Aide": "Aide",
            "Sysop": "Sysop"
        }
        category_name = category_map.get(category.name.title(), category.name.title())
        header = f"{category_name} Kommandos:"
        return header + "\n" + "  ".join(menu_lines)

    async def _show_command_help(self, session_id, command_code, user, room):
        """Show detailed help for a specific command."""
        from citadel.commands.registry import registry

        cmd_class = registry.get(command_code.upper())
        if not cmd_class:
            return ToUser(
                session_id=session_id,
                text=f"Hä? Was soll das sein: {command_code}",
                is_error=True,
                error_code="unknown_command"
            )

        if not is_allowed(cmd_class.name, user, room):
            return ToUser(
                session_id=session_id,
                text=f"Digger, du hast keine Rechte für {command_code}",
                is_error=True,
                error_code="permission_denied"
            )

        if not cmd_class.is_implemented():
            return ToUser(
                session_id=session_id,
                text=f"{cmd_class.code} - {cmd_class.short_text}\n(Noch nicht eingebaut)"
            )

        # Build detailed help text
        help_text = f"{cmd_class.code} - {cmd_class.short_text}\n{cmd_class.help_text}"

        return ToUser(
            session_id=session_id,
            text=help_text
        )


# this is a duplicate of the HelpCommand, but with a different command letter
@register_command
class MenuCommand(BaseCommand):
    code = "?"
    name = "help"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Hilfe"
    help_text = "Zeigt das Hilfemenü mit allen Kommandos."

    # Use the same implementation as HelpCommand
    run = HelpCommand.run
    _build_category_menu = HelpCommand._build_category_menu
    _show_command_help = HelpCommand._show_command_help


@register_command
class MailCommand(BaseCommand):
    code = "M"
    name = "mail"
    category = CommandCategory.UNCOMMON
    permission_level = PermissionLevel.USER
    short_text = "Postamt"
    help_text = "Geht direkt in den Mail-Raum für private Nachrichten."

    async def run(self, context):

        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        try:
            mail_room = Room(context.db, context.config, SystemRoomIDs.MAIL_ID)
            await mail_room.load()
            log.debug(f'preparing to go to room {self.args}')
        except RoomNotFoundError:
            return ToUser(
                session_id=context.session_id,
                text=f"Raum {self.args} nicht gefunden.",
                is_error=True,
                error_code="no_next_room"
            )
        context.session_mgr.set_current_room(
            context.session_id, mail_room.room_id)
        return ToUser(
            session_id=context.session_id,
            text=f"Willkommen im Raum '{mail_room.name}'."
        )


@register_command
class WhoCommand(BaseCommand):
    code = "O"
    name = "who"
    category = CommandCategory.UNCOMMON
    permission_level = PermissionLevel.USER
    short_text = "Wer ist online?"
    help_text = "Zeigt wer gerade alles rumhängt."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()

        # Check if user is privileged (aide or sysop)
        is_privileged = user.permission_level.value >= PermissionLevel.AIDE.value

        # Get all active sessions
        online_users = []
        now = datetime.now(UTC)

        with context.session_mgr.lock:
            for session_id, (session_state, last_active) in context.session_mgr.sessions.items():
                if not session_state.logged_in or not session_state.username:
                    continue

                # Load user to check public status
                online_user = User(context.db, session_state.username)
                await online_user.load()

                query = """
                    SELECT COUNT(*)
                    FROM messages
                    WHERE sender = ?
                    AND timestamp >= DATETIME('now', '-14 days')
                    AND recipient is null
                """
                result = await context.db.execute(query, (online_user.username,))
                has_posted_publicly = bool(result[0][0])

                if not is_privileged and not has_posted_publicly:
                    continue

                # Calculate activity status
                seconds_idle = (now - last_active).total_seconds()

                if is_privileged:
                    # Show granular timing for privileged users
                    if seconds_idle < 60:
                        activity_str = f"active ({int(seconds_idle)}s)"
                    elif seconds_idle < 3600:  # Less than 1 hour
                        activity_str = f"idle ({int(seconds_idle // 60)}m)"
                    else:  # 1+ hours
                        activity_str = f"idle ({int(seconds_idle // 3600)}h)"

                    if has_posted_publicly:
                        visibility = "public"
                    else:
                        visibility = "hidden"
                    user_info = f"{session_state.username} ({activity_str}) [{visibility}]"
                else:
                    # Simple active/idle for regular users
                    activity_str = "active" if seconds_idle < 60 else "idle"
                    user_info = f"{session_state.username} ({activity_str})"

                online_users.append(user_info)

        if not online_users:
            return ToUser(
                session_id=context.session_id,
                text="Alleine hier. Keiner online."
            )

        # Sort alphabetically
        online_users.sort()
        user_list = "\n".join(online_users)

        return ToUser(
            session_id=context.session_id,
            text=f"Diese Dudes sind online:\n{user_list}"
        )


@register_command
class DeleteMessageCommand(BaseCommand):
    code = "L"
    name = "delete_message"
    category = CommandCategory.COMMON
    permission_level = PermissionLevel.USER
    short_text = "Nachricht löschen"
    help_text = "Löscht eine Nachricht mit bestimmter ID. Nur Aides und Sysops dürfen fremde Nachrichten löschen."
    args = ""

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        user = User(context.db, state.username)
        await user.load()
        permission_level = user.permission_level
        room = Room(context.db, context.config, state.current_room)
        await room.load()

        if not self.args:
            return ToUser(
                session_id=context.session_id,
                text='Du musst schon ne Message-ID angeben. Nix passiert.',
                is_error=True
            )
        msg = await context.msg_mgr.get_message(self.args, user)

        allowed = False
        reason = ''
        if permission_level >= PermissionLevel.AIDE:
            allowed = True
            reason = 'is_aide'
        elif (user.username == msg['sender'] or user.username ==
              msg['recipient']):
            allowed = True
            reason = 'is_author'

        if allowed:
            await room.delete_message(msg['id'])
            log.info(
                f'Message {msg["id"]} deleted from room {room.name} by {user.username} (allowed because {reason})')
            return ToUser(
                session_id=context.session_id,
                text=f"Nachricht {msg['id']} in die Tonne gekloppt."
            )
        else:
            log.info(
                f'User {user.username} tried to delete message {msg["id"]} in room {room.name}, but was denied (no permission)')
            return ToUser(
                session_id=context.session_id,
                text=f"Finger weg! Du darfst Nachricht {msg['id']} nicht löschen.",
                is_error=True
            )


@register_command
class BlockUserCommand(BaseCommand):
    code = "B"
    name = "block_user"
    category = CommandCategory.UNUSUAL
    permission_level = PermissionLevel.USER
    short_text = "User (ent)sperren"
    help_text = "Sperrt (oder entsperrt) einen anderen User. Du siehst dann keine Nachrichten mehr von dem."


@register_command
class ValidateUsersCommand(BaseCommand):
    code = "P"
    name = "validate_users"
    category = CommandCategory.AIDE
    permission_level = PermissionLevel.AIDE
    short_text = "User freigeben"
    help_text = "Startet den Workflow um neue User zu validieren."

    async def run(self, context):
        # Check if there are any pending validations
        pending_users = await context.db.execute(
            "SELECT username, submitted_at FROM pending_validations ORDER BY submitted_at"
        )

        if not pending_users:
            return ToUser(
                session_id=context.session_id,
                text="Niemand da, der auf Freigabe wartet."
            )

        # Start validation workflow
        context.session_mgr.set_workflow(
            context.session_id,
            WorkflowState(
                kind="validate_users",
                step=1,
                data={"pending_users": [user[0]
                                        for user in pending_users], "current_index": 0}
            )
        )

        from citadel.workflows import registry as workflow_registry
        handler = workflow_registry.get("validate_users")
        if handler:
            workflow_context = WorkflowContext(
                session_id=context.session_id,
                config=context.config,
                db=context.db,
                session_mgr=context.session_mgr,
                wf_state=context.session_mgr.get_workflow(context.session_id)
            )
            return await handler.start(workflow_context)

        return ToUser(
            session_id=context.session_id,
            text="Validierungs-Workflow nicht am Start.",
            is_error=True,
            error_code="workflow_unavailable"
        )


# -------------------
# Dot commands (administrative / less common)
# -------------------

@register_command
class CreateRoomCommand(BaseCommand):
    code = ".N"
    name = "create_room"
    category = CommandCategory.UNUSUAL
    permission_level = PermissionLevel.USER
    short_text = "Raum erstellen"
    help_text = "Startet den Workflow für nen neuen Raum."

    async def run(self, context):
        # Start validation workflow
        context.session_mgr.set_workflow(
            context.session_id,
            WorkflowState(
                kind="create_room",
                step=1,
                data={}
            )
        )

        from citadel.workflows import registry as workflow_registry
        handler = workflow_registry.get("create_room")
        if handler:
            workflow_context = WorkflowContext(
                session_id=context.session_id,
                config=context.config,
                db=context.db,
                session_mgr=context.session_mgr,
                wf_state=context.session_mgr.get_workflow(context.session_id)
            )
            return await handler.start(workflow_context)

        return ToUser(
            session_id=context.session_id,
            text="Raum-Erstellungs-Workflow nicht am Start.",
            is_error=True,
            error_code="workflow_unavailable"
        )


@register_command
class EditRoomCommand(BaseCommand):
    code = ".RR"
    name = "edit_room"
    category = CommandCategory.SYSOP
    permission_level = PermissionLevel.SYSOP
    short_text = "Raum bearbeiten"
    help_text = "Ändert die Eigenschaften von diesem Raum."


@register_command
class EditUserCommand(BaseCommand):
    code = ".UB"
    name = "edit_user"
    category = CommandCategory.SYSOP
    permission_level = PermissionLevel.SYSOP
    short_text = "User bearbeiten"
    help_text = "Ändert die Eigenschaften von nem User."


@register_command
class FastForwardCommand(BaseCommand):
    code = ".S"
    name = "fast_forward"
    category = CommandCategory.UNUSUAL
    permission_level = PermissionLevel.USER
    short_text = "Vorspulen"
    help_text = "Spult direkt zur neuesten Nachricht in diesem Raum vor und überspringt den ganzen Rest."
