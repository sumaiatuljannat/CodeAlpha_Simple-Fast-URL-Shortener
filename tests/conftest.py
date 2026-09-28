"""
Pytest configuration and test fixtures for LinkSnap.
Uses an isolated in-memory or temporary SQLite test database for each test run.
"""
import os
import tempfile
import pytest

# Point to temporary test database before importing app
temp_db_fd, temp_db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_PATH"] = temp_db_path
os.environ["SECRET_KEY"] = "test-secret-key"

import database
database.DATABASE_PATH = temp_db_path

from app import app
from database import init_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    yield
    try:
        os.close(temp_db_fd)
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
    except Exception:
        pass


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client
