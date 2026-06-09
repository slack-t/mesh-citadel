import logging

from citadel.auth.permissions import PermissionLevel
from citadel.transport.packets import ToUser
from citadel.user.user import User, UserStatus
from citadel.workflows.base import Workflow, WorkflowContext, WorkflowState
from citadel.workflows.registry import register

log = logging.getLogger(__name__)


@register
class EditUserWorkflow(Workflow):
    kind = "edit_user"

    async def start(self, context: WorkflowContext) -> ToUser:
        session = context.session_mgr.get_session_state(context.session_id)
        user = user.User(session.username)
        await user.load()

        context.wf_state.data = {}

        if user.permission >= PermissionLevel.AIDE:
            context.wf_state.step = 1
            return ToUser(
                session_id=context.session_id,
                text="Welchen User willst du bearbeiten?\nTippe 'cancel' zum Abbrechen",
                hints={"type": "text", "workflow": self.kind, "step": 1}
            )
        else:
            context.wf_state.step = 2
            context.wf_state.data["target_user"] = user.username
            return await self._present_edit_menu(context, user)

    async def handle(self, context: WorkflowContext, command: str) -> ToUser | None:
        db = context.db
        session = context.session_mgr.get_session_state(context.session_id)
        editor = await db.get_user(session.username)

        step = context.wf_state.step
        data = context.wf_state.data

        if step == 1:
            if editor.permission in {PermissionLevel.AIDE, PermissionLevel.SYSOP}:
                username = command.strip()
                target = await db.get_user(username)
                if not target:
                    return ToUser(
                        session_id=context.session_id,
                        text="User nicht gefunden. Gib nen echten Namen ein oder tippe 'cancel'.",
                        is_error=True,
                        error_code="user_not_found"
                    )
                data["target_user"] = target.username
            else:
                data["target_user"] = editor.username

            context.wf_state.step = 2
            return await self._present_edit_menu(context, editor)

        if step == 2:
            try:
                choice = int(command.strip())
            except ValueError:
                return await self._present_edit_menu(context, editor)

            options = self._menu_options(editor)
            if choice < 1 or choice > len(options):
                return await self._present_edit_menu(context, editor)

            selected = options[choice - 1]
            data["field"] = selected

            if selected == "Abbrechen":
                context.session_mgr.clear_workflow(context.session_id)
                return ToUser(
                    session_id=context.session_id,
                    text="Bearbeiten abgebrochen. Ciao!"
                    # TODO: have to figure out how to signal this needs a
                    # prompt added
                )
            elif selected == "Passwort zurücksetzen":
                log.info(
                    f"{editor.username} initiated password reset for {data['target_user']}")
                context.wf_state.kind = "reset_password"
                context.wf_state.step = 1
                context.wf_state.data = data
                context.session_mgr.set_workflow(context.session_id, context)
                return ToUser(
                    session_id=context.session_id,
                    text="Passwort zurücksetzen\nAltes Passwort eingeben:",
                    hints={"type": "text", "workflow": "reset_password", "step": 1}
                )
            elif selected == "Anzeigename":
                context.wf_state.step = 3
                target = await db.get_user(data["target_user"])
                return ToUser(
                    session_id=context.session_id,
                    text=f"Aktueller Anzeigename: {target.display_name}\nNeuer Anzeigename her:",
                    hints={"type": "text", "workflow": self.kind, "step": 3}
                )
            elif selected == "Rechte-Level":
                context.wf_state.step = 4
                levels = []
                # don't allow aides to assign sysop level
                for level in PermissionLevel:
                    if level <= editor.permission:
                        levels.append(level)
                return ToUser(
                    session_id=context.session_id,
                    text="Wähle das neue Rechte-Level:\n" + "\n".join(
                        f"{i+1}. {level.name}" for i, level in levels
                    ),
                    hints={"type": "menu", "workflow": self.kind, "step": 4}
                )
            elif selected == "Status":
                context.wf_state.step = 5
                return ToUser(
                    session_id=context.session_id,
                    text="Wähle den neuen Status:\n" + "\n".join(
                        f"{i+1}. {status.name}" for i, status in enumerate(UserStatus)
                    ),
                    hints={"type": "menu", "workflow": self.kind, "step": 5}
                )

        if step == 3: # display name change
            new_name = command.strip()
            target = await db.get_user(data["target_user"])
            old = target.display_name
            await db.update_user(target.username, display_name=new_name)
            log.info(
                f"{editor.username} changed display name for {target.username} from '{old}' to '{new_name}'")
            context.wf_state.step = 2
            return await self._present_edit_menu(context, editor)

        if step == 4: # permission level change
            try:
                index = int(command.strip()) - 1
                new_perm = list(PermissionLevel)[index]
            except (ValueError, IndexError):
                return ToUser(
                    session_id=context.session_id,
                    text="Falsche Wahl, Digger. Wähl was Gültiges aus.",
                    is_error=True,
                    error_code="invalid_permission"
                )
            target = await db.get_user(data["target_user"])
            old = target.permission
            await db.update_user(target.username, permission=new_perm)
            log.info(
                f"{editor.username} changed permission for {target.username} from {old.name} to {new_perm.name}")
            context.wf_state.step = 2
            return await self._present_edit_menu(context, editor)

        if step == 5: # account status change
            try:
                index = int(command.strip()) - 1
                new_status = list(UserStatus)[index]
            except (ValueError, IndexError):
                return ToUser(
                    session_id=context.session_id,
                    text="Falsche Wahl, Digger. Wähl nen gültigen Status.",
                    is_error=True,
                    error_code="invalid_status"
                )
            target = await db.get_user(data["target_user"])
            old = target.status
            await db.update_user(target.username, status=new_status)
            log.info(
                f"{editor.username} changed status for {target.username} from {old.name} to {new_status.name}")
            context.wf_state.step = 2
            return await self._present_edit_menu(context, editor)

    async def _present_edit_menu(self, context: WorkflowContext, editor: User) -> ToUser:
        db = context.db
        data = context.wf_state.data
        target = await db.get_user(data["target_user"])

        options = self._menu_options(editor)
        lines = []
        for option in options:
            if option == "Anzeigename":
                lines.append(f"Anzeigename: {target.display_name}")
            elif option == "Rechte-Level":
                lines.append(f"Rechte-Level: {target.permission.name}")
            elif option == "Status":
                lines.append(f"Status: {target.status.name}")
            elif option == "Passwort zurücksetzen":
                lines.append("Passwort zurücksetzen")
            elif option == "Abbrechen":
                lines.append("Abbrechen")

        return ToUser(
            session_id=context.session_id,
            text=f"Benutzername: {target.username}\n" + "\n".join(
                f"{i+1}. {opt}" for i, opt in enumerate(options)
            ),
            hints={"type": "menu", "workflow": self.kind, "step": 2}
        )

    def _menu_options(self, editor: User) -> list[str]:
        options = ["Anzeigename", "Passwort zurücksetzen"]
        if editor.permission >= PermissionLevel.AIDE:
            options.extend(["Rechte-Level", "Status"]) 
        options.append("Abbrechen")
        return options
