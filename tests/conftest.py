"""Pytest configuration and fixtures."""

import os
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def e2e_db_path():
    """Create and initialize fresh e2e.db for entire test session.
    
    Database path can be overridden with E2E_DB_PATH environment variable.
    Database is deleted after test session completes.
    """
    db_path = os.getenv("E2E_DB_PATH", "e2e.db")
    db_path = str(Path(db_path).resolve())
    
    # Delete existing database if present
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # Run migrations to initialize database
    from migrate import migrate
    migrate(db_path)
    
    yield db_path
    
    # Clean up after test session
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture(autouse=True)
def reset_database(e2e_db_path: str):  # type: ignore[no-untyped-def]
    """Delete and recreate database before each test."""
    # Delete database before test
    if os.path.exists(e2e_db_path):
        os.remove(e2e_db_path)
    
    # Recreate with fresh schema
    from migrate import migrate
    migrate(e2e_db_path)
    
    yield
    
    # Cleanup happens in e2e_db_path fixture's cleanup
