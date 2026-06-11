import pytest
from unittest.mock import AsyncMock

from citadel.workflows.login import LoginWorkflow
from citadel.workflows.base import WorkflowContext, WorkflowState
from citadel.transport.packets import ToUser


def _context(session_mgr, db, config, step, data=None):
    session_id = session_mgr.create_session()
    wf_state = WorkflowState(kind="login", step=step, data=data or {})
    session_mgr.set_workflow(session_id, wf_state)
    return WorkflowContext(
        session_id=session_id, db=db, config=config,
        session_mgr=session_mgr, wf_state=wf_state, locale="de",
    )


@pytest.mark.asyncio
async def test_unknown_user_triggers_retry(session_mgr, db, config):
    ctx = _context(session_mgr, db, config, step=2)
    response = await LoginWorkflow().handle(ctx, "ghost")  # no such user
    assert isinstance(response, ToUser)
    assert response.is_error
    assert response.error_code == "invalid_username"


@pytest.mark.asyncio
async def test_new_user_triggers_registration(session_mgr, db, config):
    ctx = _context(session_mgr, db, config, step=2)
    response = await LoginWorkflow().handle(ctx, "new")
    assert isinstance(response, ToUser)
    # Should hand off to the registration workflow.
    assert response.hints.get("workflow") == "register_user"


@pytest.mark.asyncio
async def test_failed_password_triggers_retry(session_mgr, db, config, monkeypatch):
    monkeypatch.setattr("citadel.workflows.login.authenticate",
                        AsyncMock(return_value=None))
    ctx = _context(session_mgr, db, config, step=3, data={"username": "bob"})
    response = await LoginWorkflow().handle(ctx, "wrong-password")
    assert isinstance(response, ToUser)
    assert response.is_error
    assert response.error_code == "login_failed"


@pytest.mark.asyncio
async def test_login_blocked_after_three_attempts(session_mgr, db, config, monkeypatch):
    monkeypatch.setattr("citadel.workflows.login.authenticate",
                        AsyncMock(return_value=None))
    ctx = _context(session_mgr, db, config, step=3,
                   data={"username": "bob", "attempts": 2})
    response = await LoginWorkflow().handle(ctx, "still-wrong")
    assert isinstance(response, ToUser)
    assert response.is_error
    assert response.error_code == "login_blocked"


@pytest.mark.asyncio
async def test_invalid_step_returns_error(session_mgr, db, config):
    ctx = _context(session_mgr, db, config, step=99)
    response = await LoginWorkflow().handle(ctx, "anything")
    assert isinstance(response, ToUser)
    assert response.is_error
    assert response.error_code == "invalid_login_step"
