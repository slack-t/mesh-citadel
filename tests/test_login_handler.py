import pytest
from unittest.mock import AsyncMock, MagicMock

from citadel.auth.passwords import authenticate


@pytest.fixture
def mock_user(monkeypatch):
    # Replace the whole User class with a MagicMock whose classmethods are
    # AsyncMocks and whose constructor returns an instance with an async load().
    instance = MagicMock()
    instance.load = AsyncMock()

    user_cls = MagicMock(return_value=instance)
    user_cls.username_exists = AsyncMock()
    user_cls.verify_password = AsyncMock()
    user_cls.get_actual_username = AsyncMock()

    monkeypatch.setattr("citadel.user.user.User", user_cls)
    # authenticate() sleeps 5s on a failed login (anti-brute-force); skip it.
    monkeypatch.setattr("citadel.auth.passwords.time.sleep", lambda *a, **k: None)

    return {
        'instance': instance,
        'username_exists': user_cls.username_exists,
        'verify_password': user_cls.verify_password,
        'get_actual_username': user_cls.get_actual_username,
    }


@pytest.fixture
def db_mgr():
    return MagicMock()


@pytest.mark.asyncio
async def test_successful_authentication(mock_user, db_mgr):
    mock_user['username_exists'].return_value = "alice"
    mock_user['get_actual_username'].return_value = "alice"
    mock_user['verify_password'].return_value = True

    result = await authenticate(db_mgr, "alice", "correct-password")

    assert result is mock_user['instance']


@pytest.mark.asyncio
async def test_failed_password(mock_user, db_mgr):
    mock_user['username_exists'].return_value = "alice"
    mock_user['get_actual_username'].return_value = "alice"
    mock_user['verify_password'].return_value = False

    result = await authenticate(db_mgr, "alice", "wrong-password")

    assert result is None


@pytest.mark.asyncio
async def test_unknown_user(mock_user, db_mgr):
    mock_user['username_exists'].return_value = None

    result = await authenticate(db_mgr, "newuser", "irrelevant")

    assert result is None
