import pytest
from freezegun import freeze_time

from citadel.session.manager import SessionManager


class MockConfig:
    def __init__(self, timeout=10):
        self.auth = {"session_timeout": timeout}


class MockDB:
    async def execute(self, query, params=()):
        return []


@pytest.fixture
def session_mgr():
    return SessionManager(MockConfig(timeout=10), MockDB())


@pytest.mark.asyncio
async def test_sweeper_expires_stale_sessions(session_mgr):
    with freeze_time("2025-09-17 00:00:00") as frozen:
        session_id = session_mgr.create_session()
        session_mgr.mark_username(session_id, "alice")
        assert session_mgr.get_session_state(session_id).username == "alice"

        # Advance time past the timeout, then sweep.
        frozen.move_to("2025-09-17 00:00:11")
        session_mgr.sweep_expired_sessions()

        assert session_mgr.get_session_state(session_id) is None


@pytest.mark.asyncio
async def test_sweeper_preserves_active_sessions(session_mgr):
    with freeze_time("2025-09-17 00:00:00") as frozen:
        session_id = session_mgr.create_session()
        session_mgr.mark_username(session_id, "bob")
        assert session_mgr.get_session_state(session_id).username == "bob"

        # Advance time to just before the timeout; sweep should keep it.
        frozen.move_to("2025-09-17 00:00:09")
        session_mgr.sweep_expired_sessions()

        assert session_mgr.get_session_state(session_id).username == "bob"
