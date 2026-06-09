# citadel/workflows/register_user.py

from datetime import datetime, UTC
import logging
import string

from citadel.auth.passwords import generate_salt, hash_password
from citadel.auth.permissions import PermissionLevel
from citadel.room.room import Room
from citadel.transport.packets import ToUser
from citadel.user.user import User, UserStatus
from citadel.workflows.base import Workflow, WorkflowState, WorkflowContext
from citadel.workflows.registry import register

log = logging.getLogger(__name__)


def is_ascii_username(username: str) -> bool:
    return all(c in string.ascii_letters + string.digits + "_-" for c in username)


@register
class RegisterUserWorkflow(Workflow):
    kind = "register_user"

    async def start(self, context):
        """Start the registration workflow by prompting for username."""
        text = "1: Registration\n\nSpitzname (Username):"
        return ToUser(
            session_id=context.session_id,
            text=text,
            hints={"type": "text", "workflow": self.kind, "step": 1}
        )

    async def handle(self, context, command):
        db = context.db

        step = context.wf_state.step
        data = context.wf_state.data

        if not 'step_num' in data:
            step_num = 2
            data['step_num'] = step_num
        else:
            step_num = data['step_num'] + 1
            data['step_num'] = step_num

        # Cancellation is handled by transport layer, no need to check here

        # Step 1: Username
        if step == 1:
            username = command.strip() if command else ""
            forbidden = context.config.bbs.get('forbidden_usernames', [])
            forbidden.append("citadel") # citadel is always reserved
            if username.lower() in forbidden:
                return ToUser(
                    session_id=context.session_id,
                    text=f"'{username}' ist reserviert und darf nicht benutzt werden.\nSpitzname (Username):",
                    is_error=True,
                    error_code="invalid_username",
                    hints={"type": "text", "workflow": self.kind, "step": 1}
                )
            if not is_ascii_username(username):
                return ToUser(
                    session_id=context.session_id,
                    text="Benutzernamen dürfen nur aus normalen (ASCII) Zeichen bestehen\nSpitzname (Username):",
                    is_error=True,
                    error_code="invalid_username",
                    hints={"type": "text", "workflow": self.kind, "step": 1}
                )
            if not username or len(username) < 3:
                return ToUser(
                    session_id=context.session_id,
                    text="Benutzername muss mindestens 3 Zeichen lang sein\nSpitzname (Username):",
                    is_error=True,
                    error_code="invalid_username",
                    hints={"type": "text", "workflow": self.kind, "step": 1}
                )
            if await User.username_exists(db, username):
                return ToUser(
                    session_id=context.session_id,
                    text=f"'{username}' ist leider schon vergeben\nSpitzname (Username):",
                    is_error=True,
                    error_code="username_taken",
                    hints={"type": "text", "workflow": self.kind, "step": 1}
                )

            # Create provisional user immediately with temporary credentials
            temp_salt = generate_salt()
            temp_password_hash = hash_password("temporary", temp_salt)

            await User.create(
                context.config,
                db,
                username,
                temp_password_hash,
                temp_salt,
                username,  # Use username as initial display name
                UserStatus.ACTIVE  # Users start as ACTIVE with UNVERIFIED permissions
            )

            # Update existing session with the new username
            context.session_mgr.mark_username(context.session_id, username)

            data["username"] = username
            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=2, data=data)
            )

            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Wie sollen dich andere nennen? (Anzeigename):",
                hints={"type": "text", "workflow": self.kind, "step": 2}
            )

        # Step 2: Display Name
        if step == 2:
            display_name = command
            if not display_name:
                return ToUser(
                    session_id=context.session_id,
                    text="Anzeigename darf nicht leer sein, Digger.",
                    is_error=True,
                    error_code="invalid_display_name"
                )

            # Update the provisional user's display name
            username = data["username"]
            user = User(db, username)
            await user.load()
            await user.set_display_name(display_name)

            data["display_name"] = display_name
            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=3, data=data)
            )
            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Such dir ein knackiges Passwort aus:",
                hints={"type": "password", "workflow": self.kind, "step": 3}
            )

        # Step 3: Password
        if step == 3:
            password = command
            if not password or len(password) < 6:
                return ToUser(
                    session_id=context.session_id,
                    text="Dein Passwort muss mindestens 6 Zeichen lang sein. Sei mal n bisschen kreativ!",
                    is_error=True,
                    error_code="invalid_password"
                )

            # Update the provisional user's password
            username = data["username"]
            user = User(db, username)
            await user.load()
            new_salt = generate_salt()
            new_password_hash = hash_password(password, new_salt)
            await user.update_password(new_password_hash, new_salt)
            try:
                terms_req = context.config.bbs["registration"]["terms_required"]
                if terms_req:
                    terms = context.config.bbs["registration"]["terms"]
                    context.session_mgr.set_workflow(
                        context.session_id,
                        WorkflowState(kind=self.kind, step=4, data=data)
                    )
                    return ToUser(
                        session_id=context.session_id,
                        text=f"{step_num}: {terms}\nBist du cool mit den Regeln? (ja/nein)",
                        hints={"type": "choice", "options": [
                            "ja", "nein"], "workflow": self.kind, "step": 4}
                    )
                else:
                    log.warning("Terms agreement disabled, skipping")
            except KeyError:
                log.warning("No terms configured, skipping terms agreement")
            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=5, data=data)
            )
            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Was ist dein Motto?",
                hints={"type": "text", "workflow": self.kind, "step": 5}
            )

        # Step 4: Terms
        if step == 4:
            agree = command.lower() if command else ""
            if agree not in ("ja", "j", "yes", "y"):
                # Track rejection attempts
                reject_count = data.get("terms_reject_count", 0) + 1
                data["terms_reject_count"] = reject_count

                if reject_count >= 3:
                    # User has rejected terms 3 times, cancel registration
                    await self.cleanup(context)
                    context.session_mgr.clear_workflow(context.session_id)

                    # Start login workflow to return user to login prompt
                    session_id, login_prompt = await context.session_mgr.start_login_workflow(
                        context.config, context.db, context.session_id
                    )

                    if login_prompt:
                        login_prompt.text = "Wer die Regeln nicht mag, fliegt raus.\n\n" + login_prompt.text
                        return login_prompt
                    else:
                        return ToUser(
                            session_id=session_id,
                            text="Registrierung in die Tonne gekloppt. Komm wieder, wenn du mutiger bist.",
                            is_error=True,
                            error_code="terms_rejected_final"
                        )

                # Give another chance
                context.session_mgr.set_workflow(
                    context.session_id,
                    WorkflowState(kind=self.kind, step=4, data=data)
                )

                attempts_left = 3 - reject_count
                terms = context.config.bbs["registration"]["terms"]
                return ToUser(
                    session_id=context.session_id,
                    text=(f"{step_num}: Du musst den Regeln zustimmen! "
                          f"{attempts_left} Versuche übrig.\n\n{terms}\nEinverstanden?"),
                    hints={"type": "choice", "options": [
                        "ja", "nein"], "workflow": self.kind, "step": 4}
                )
            data["agreed"] = True
            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=5, data=data)
            )
            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Was ist dein Motto?",
                hints={"type": "text", "workflow": self.kind, "step": 5}
            )

        # Step 5: Intro
        if step == 5:
            intro = command
            data["intro"] = intro
            context.session_mgr.set_workflow(
                context.session_id,
                WorkflowState(kind=self.kind, step=6, data=data)
            )
            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Registrierung abschicken? (ja/nein)",
                hints={"type": "choice", "options": [
                    "ja", "nein"], "workflow": self.kind, "step": 6}
            )

        # Step 6: Finalize
        if step == 6:
            confirm = command.lower() if command else ""
            if confirm not in ("ja", "j", "yes", "y"):
                return ToUser(
                    session_id=context.session_id,
                    text="Registrierung abgebrochen. Na gut, dann halt nicht.",
                    is_error=True,
                    error_code="registration_cancelled"
                )
            # Check if this is the first user (before activation)
            username = data["username"]
            user = User(db, username)
            await user.load()

            user_count = await User.get_user_count(db)
            if user_count == 1:  # This is the first and only user
                # First user becomes sysop automatically (no validation needed)
                await user.set_status(UserStatus.ACTIVE)
                await user.set_permission_level(PermissionLevel.SYSOP)
                await context.session_mgr.mark_logged_in(context.session_id)
                context.session_mgr.clear_workflow(context.session_id)
                return ToUser(
                    session_id=context.session_id,
                    text=f"{step_num}: Moin Sysop! Du bist der Boss und hast jetzt alle Rechte.",
                    hints={"prompt_next": True}
                )
            else:
                # Subsequent users get limited access until validated
                # Store user registration for validation
                await db.execute(
                    "INSERT INTO pending_validations "
                    "(username, submitted_at, transport_engine, transport_metadata, intro_text) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        username,
                        datetime.now(UTC).isoformat(),
                        "cli",
                        "{}",
                        data.get("intro", "")
                    )
                )
                # Keep user logged in with UNVERIFIED access
                await context.session_mgr.mark_logged_in(context.session_id)

            context.session_mgr.clear_workflow(context.session_id)
            await Room.system_log(db, context.config,
                f"New user {data['display_name']} ({username}) registered")
            return ToUser(
                session_id=context.session_id,
                text=f"{step_num}: Boom! Registriert! Du darfst aber noch nicht viel machen, bis du gecheckt wurdest."
            )

        return ToUser(
            session_id=context.session_id,
            text=f"Kein Plan was Schritt {step} im Workflow {self.kind} soll",
            is_error=True,
            error_code="invalid_step"
        )

    async def cleanup(self, context):
        """Clean up registration workflow when cancelled.

        Removes any provisional user created during registration and
        resets session to anonymous state.
        """
        step = context.wf_state.step
        data = context.wf_state.data

        # If we created a provisional user (step >= 1), remove it
        if step >= 1 and "username" in data:
            username = data["username"]

            # Check if user exists and is provisional
            user = User(context.db, username)
            try:
                await user.load()
            except RuntimeError:
                # User doesn't exist - nothing to clean up
                return

            if user.permission_level == PermissionLevel.UNVERIFIED:
                try:
                    await context.db.execute(
                        "DELETE FROM users WHERE username = ? AND permission_level = ?",
                        (username, PermissionLevel.UNVERIFIED.value)
                    )
                    log.info(
                        f"Deleted provisional user '{username}' during workflow cancellation")
                except RuntimeError as e:
                    log.error(
                        f"Failed to delete provisional user '{username}': {e}")
            else:
                log.warning(
                    f"User '{username}' was not provisional during cleanup (status: {user.status})")
                log.warning(f"'{username}' not cleaned up")

            # Reset session to anonymous state
            context.session_mgr.mark_username(context.session_id, None)
            log.info(
                f"Reset session '{context.session_id}' to anonymous state")
            # Note: Login workflow will be started by the cancel command
