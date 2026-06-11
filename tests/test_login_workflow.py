import pytest

from citadel.auth.permissions import PermissionLevel
from citadel.auth.passwords import generate_salt, hash_password
from citadel.user.user import User, UserStatus
from citadel.workflows.login import LoginWorkflow
from citadel.workflows.base import WorkflowContext, WorkflowState
from citadel.transport.packets import ToUser


async def _make_user(db, config, username, password):
    salt = generate_salt()
    await User.create(config, db, username, hash_password(password, salt),
                      salt, username, UserStatus.ACTIVE)
    user = User(db, username)
    await user.load()
    await user.set_permission_level(PermissionLevel.USER)


def _context(session_mgr, db, config, step, data=None):
    session_id = session_mgr.create_session()
    wf_state = WorkflowState(kind="login", step=step, data=data or {})
    session_mgr.set_workflow(session_id, wf_state)
    return WorkflowContext(
        session_id=session_id, db=db, config=config,
        session_mgr=session_mgr, wf_state=wf_state, locale="de",
    )


@pytest.mark.asyncio
async def test_login_step1_prompts_for_username(session_mgr, db, config):
    ctx = _context(session_mgr, db, config, step=1)
    response = await LoginWorkflow().handle(ctx, None)
    assert isinstance(response, ToUser)
    assert not response.is_error
    assert response.hints.get("type") == "text"
    assert response.hints.get("step") == 2


@pytest.mark.asyncio
async def test_login_step2_known_user_prompts_password(session_mgr, db, config):
    await _make_user(db, config, "bob", "correct-password")
    ctx = _context(session_mgr, db, config, step=2)
    response = await LoginWorkflow().handle(ctx, "bob")
    assert not response.is_error
    assert response.hints.get("type") == "password"
    assert response.hints.get("step") == 3


@pytest.mark.asyncio
async def test_login_step3_success(session_mgr, db, config):
    await _make_user(db, config, "bob", "correct-password")
    ctx = _context(session_mgr, db, config, step=3, data={"username": "bob"})
    response = await LoginWorkflow().handle(ctx, "correct-password")

    assert not response.is_error
    assert "bob" in response.text
    # Session should now be logged in, bound to bob, with the workflow cleared.
    assert session_mgr.get_username(ctx.session_id) == "bob"
    assert session_mgr.is_logged_in(ctx.session_id) is True
    assert session_mgr.get_workflow(ctx.session_id) is None
