@register_command
class KillRoomCommand(BaseCommand):
    code = ".KR"
    name = "kill_room"
    category = CommandCategory.SYSOP
    permission_level = PermissionLevel.SYSOP
    short_text = "Raum löschen"
    help_text = "Löscht den aktuellen Raum samt allen Nachrichten endgültig. (Nur für Sysops, Systemräume können nicht gelöscht werden)."

    async def run(self, context):
        state = context.session_mgr.get_session_state(context.session_id)
        if not state or not state.current_room:
            return ToUser(session_id=context.session_id, text="Du bist in gar keinem Raum, Digger.", is_error=True)
            
        from citadel.room.room import Room
        try:
            room = Room(context.db, context.config, state.current_room)
            room_name = room.name
            
            # Change user to lobby before deleting
            lobby_id = await room.get_id_by_name("Lobby")
            context.session_mgr.set_current_room(context.session_id, lobby_id)
            
            await room.delete_room(state.username)
            return ToUser(
                session_id=context.session_id,
                text=f"BÄM! Raum '{room_name}' wurde komplett vaporisiert und du wurdest in die Lobby teleportiert."
            )
        except ValueError as e:
            return ToUser(session_id=context.session_id, text=f"Fehler: {str(e)}", is_error=True)
        except Exception as e:
            return ToUser(session_id=context.session_id, text=f"Fehler beim Löschen: {str(e)}", is_error=True)
