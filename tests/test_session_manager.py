import pytest
from datetime import datetime, timedelta, UTC
from citadel.room.room import SystemRoomIDs
from citadel.session.manager import SessionManager
from citadel.workflows.base import WorkflowState


class MockConfig:
    def __init__(self, timeout=3600):
        self.auth = {"session_timeout": timeout}


class MockDB:
    """Minimal stand-in for DatabaseManager. SessionManager only needs it
    stored on the instance; the current create_session() is anonymous and
    does not touch the DB."""

    def __init__(self, fail=False):
        self.fail = fail

    async def execute(self, query, params=()):
        if self.fail:
            raise RuntimeError("Simulated DB failure")
        return []


@pytest.fixture
def session_mgr():
    config = MockConfig(timeout=10)  # short timeout for testing
    db = MockDB()
    return SessionManager(config, db)


@pytest.mark.asyncio
async def test_create_session_is_anonymous_then_bind_username(session_mgr):
    # create_session() is synchronous and creates an anonymous session;
    # the username is bound later (at login) via mark_username().
    session_id = session_mgr.create_session()
    assert isinstance(session_id, str)

    state = session_mgr.get_session_state(session_id)
    assert state is not None
    assert state.username is None
    assert state.logged_in is False

    session_mgr.mark_username(session_id, "alice")
    assert session_mgr.get_session_state(session_id).username == "alice"


@pytest.mark.asyncio
async def test_touch_session_extends_activity(session_mgr):
    session_id = session_mgr.create_session()
    session_mgr.mark_username(session_id, "bob")
    assert session_mgr.touch_session(session_id) is True
    assert session_mgr.get_session_state(session_id).username == "bob"


@pytest.mark.asyncio
async def test_expire_session_manually(session_mgr):
    session_id = session_mgr.create_session()
    assert await session_mgr.expire_session(session_id) is True
    assert session_mgr.get_session_state(session_id) is None


@pytest.mark.asyncio
async def test_get_state_returns_even_if_stale(session_mgr):
    session_id = session_mgr.create_session()
    session_mgr.mark_username(session_id, "bob")

    # Simulate staleness by backdating the last-activity timestamp.
    with session_mgr.lock:
        state, _ = session_mgr.sessions[session_id]
        session_mgr.sessions[session_id] = (
            state,
            datetime.now(UTC) - timedelta(seconds=999),
        )

    # get_session_state still returns the state until the sweeper runs.
    assert session_mgr.get_session_state(session_id).username == "bob"


@pytest.mark.asyncio
async def test_expire_session_nonexistent_session_id(session_mgr):
    assert await session_mgr.expire_session("invalid-session_id") is False


@pytest.mark.asyncio
async def test_touch_session_invalid_session_id(session_mgr):
    assert session_mgr.touch_session("invalid-session_id") is False


@pytest.mark.asyncio
async def test_get_state_invalid_session_id(session_mgr):
    assert session_mgr.get_session_state("invalid-session_id") is None


@pytest.mark.asyncio
async def test_current_room_helpers(session_mgr):
    session_id = session_mgr.create_session()

    # New sessions default to the Lobby.
    room = session_mgr.get_current_room(session_id)
    assert room in (None, SystemRoomIDs.LOBBY_ID)

    # Change room and verify.
    session_mgr.set_current_room(session_id, "TechTalk")
    assert session_mgr.get_current_room(session_id) == "TechTalk"

    # Invalid session_id should return None and not raise.
    assert session_mgr.get_current_room("invalid") is None
    session_mgr.set_current_room("invalid", "Nowhere")  # should be a no-op


@pytest.mark.asyncio
async def test_workflow_state_lifecycle(session_mgr):
    session_id = session_mgr.create_session()

    # Initially no workflow.
    assert session_mgr.get_workflow(session_id) is None

    # Set a workflow.
    wf = WorkflowState(kind="validate_users", step=1,
                       data={"pending": ["alice"]})
    session_mgr.set_workflow(session_id, wf)
    got = session_mgr.get_workflow(session_id)
    assert got.kind == "validate_users"
    assert got.step == 1
    assert got.data["pending"] == ["alice"]

    # Clear workflow.
    session_mgr.clear_workflow(session_id)
    assert session_mgr.get_workflow(session_id) is None

    # Invalid session_id should be safe.
    assert session_mgr.get_workflow("invalid") is None
    session_mgr.set_workflow("invalid", wf)  # should be a no-op
    session_mgr.clear_workflow("invalid")    # should be a no-op
