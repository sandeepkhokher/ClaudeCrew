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
    application = create_app({"TESTING": True, "DATABASE": path})
    yield application
    os.close(fd)
    os.unlink(path)


@pytest.fixture
def client(app):
    return app.test_client()
