"""Shared pytest fixtures for mesh-citadel-ng tests.

Provides a lightweight DummyConfig plus real (temp-file) DatabaseManager and
SessionManager fixtures, so workflow/command tests can run against the real
code paths instead of brittle mocks.

Note: test modules that define their own `config` / `db` / `session_mgr`
fixtures override these for that module.
"""

import os
import tempfile

import pytest
import pytest_asyncio

from citadel.db.manager import DatabaseManager
from citadel.db.initializer import initialize_database


class DummyConfig:
    """Minimal stand-in for citadel.config.Config with the keys the code reads."""

    def __init__(self, db_path):
        self.database = {'db_path': db_path}  # no use_memory -> plain disk DB
        self.logging = {'log_file_path': '/tmp/citadel-test.log',
                        'log_level': 'DEBUG'}
        self.auth = {'session_timeout': 3600, 'password_cache_duration': 14}
        self.bbs = {
            'max_messages_per_room': 100,
            'max_rooms': 50,
            'max_users': 300,
            'mail_message_limit': 50,
            'starting_room': 'Lobby',
            'system_events_room': 'System',
            'welcome_message': 'Welcome to the test BBS!',
            'timezone': 'UTC',
            'date_format': '%d%b%y %H:%M',
            'room_names': {
                'lobby': 'Lobby', 'mail': 'Mail', 'aides': 'Aides',
                'sysop': 'Sysop', 'system': 'System', 'twit': 'Purgatory',
            },
        }
        self.transport = {
            'meshcore': {'max_packet_size': 150},
            'cli': {'socket': '/tmp/mesh-citadel-test.sock'},
        }
        self.version = 'test'


@pytest.fixture
def config():
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    tmp.close()
    cfg = DummyConfig(tmp.name)
    yield cfg
    try:
        os.unlink(tmp.name)
    except OSError:
        pass


@pytest_asyncio.fixture
async def db(config):
    DatabaseManager._instance = None
    db_mgr = DatabaseManager(config)
    await db_mgr.start()
    await initialize_database(db_mgr, config)
    yield db_mgr
    await db_mgr.shutdown()
    DatabaseManager._instance = None


@pytest_asyncio.fixture
async def session_mgr(config, db):
    from citadel.session.manager import SessionManager
    return SessionManager(config, db)
