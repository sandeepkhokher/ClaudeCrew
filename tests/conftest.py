"""Shared pytest fixtures.

Each test gets a fresh app backed by a temporary SQLite file, so tests are fully
isolated and never touch the real database.
"""

import os
import tempfile

import pytest

from app import create_app


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".db")
    # RESET_TOKEN_IN_RESPONSE defaults to False (fail-closed) so production
    # never leaks tokens. Tests need the raw token echoed back to drive the
    # reset flow, so force it on for the shared client/app fixtures.
    application = create_app({"TESTING": True, "DATABASE": path, "RESET_TOKEN_IN_RESPONSE": True})
    yield application
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()
