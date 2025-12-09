"""Tests for CSRF protection in the feed-baby application."""

import pytest
import tempfile
from pathlib import Path
from fastapi.testclient import TestClient
from fastapi import FastAPI

from migrate import migrate
from feed_baby import bootstrap_server
from feed_baby.feed import Feed
from decimal import Decimal


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        migrate(db_path)
        yield db_path


@pytest.fixture
def client(test_db):
    """Create a test client with a test database."""
    app = FastAPI()
    bootstrap_server(app, test_db)
    return TestClient(app)


def test_home_page_includes_csrf_token(client, test_db):
    """Test that the home page includes a CSRF token when feeds exist."""
    # Create a feed first so the home page shows the delete form
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    response = client.get("/")
    assert response.status_code == 200
    assert "csrf_token" in response.text
    assert "session_id" in response.cookies


def test_feed_form_includes_csrf_token(client):
    """Test that the feed form includes a CSRF token."""
    response = client.get("/feed")
    assert response.status_code == 200
    assert "csrf_token" in response.text
    assert "session_id" in response.cookies


def test_create_feed_requires_csrf_token(client):
    """Test that creating a feed requires a valid CSRF token."""
    # First, get the form to obtain a CSRF token
    form_response = client.get("/feed")
    session_id = form_response.cookies.get("session_id")
    
    # Extract CSRF token from the response
    import re
    token_match = re.search(r'name="csrf_token" value="([^"]+)"', form_response.text)
    assert token_match is not None
    csrf_token = token_match.group(1)
    
    # Try to create a feed with a valid CSRF token
    response = client.post(
        "/feed",
        data={
            "ounces": "3.0",
            "time": "12:00",
            "date": "2025-12-09",
            "timezone": "UTC",
            "csrf_token": csrf_token,
        },
        cookies={"session_id": session_id},
        follow_redirects=False,
    )
    assert response.status_code == 303  # Redirect on success


def test_create_feed_rejects_invalid_csrf_token(client):
    """Test that creating a feed rejects an invalid CSRF token."""
    # Get a session ID but use an invalid token
    form_response = client.get("/feed")
    session_id = form_response.cookies.get("session_id")
    
    # Try to create a feed with an invalid CSRF token
    response = client.post(
        "/feed",
        data={
            "ounces": "3.0",
            "time": "12:00",
            "date": "2025-12-09",
            "timezone": "UTC",
            "csrf_token": "invalid_token_12345",
        },
        cookies={"session_id": session_id},
        follow_redirects=False,
    )
    assert response.status_code == 403  # Forbidden


def test_create_feed_rejects_missing_csrf_token(client):
    """Test that creating a feed rejects missing CSRF token."""
    response = client.post(
        "/feed",
        data={
            "ounces": "3.0",
            "time": "12:00",
            "date": "2025-12-09",
            "timezone": "UTC",
            # No csrf_token
        },
        follow_redirects=False,
    )
    assert response.status_code == 422  # Unprocessable Entity (missing required field)


def test_delete_feed_requires_csrf_token(client, test_db):
    """Test that deleting a feed requires a valid CSRF token."""
    # First, create a feed
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    # Get all feeds to find the ID
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1
    feed_id = feeds[0].id
    
    # Get a CSRF token
    home_response = client.get("/")
    session_id = home_response.cookies.get("session_id")
    
    import re
    token_match = re.search(r'name="csrf_token" value="([^"]+)"', home_response.text)
    assert token_match is not None
    csrf_token = token_match.group(1)
    
    # Try to delete with a valid CSRF token
    response = client.post(
        f"/feed/{feed_id}/delete",
        data={"csrf_token": csrf_token},
        cookies={"session_id": session_id},
        follow_redirects=False,
    )
    assert response.status_code == 303  # Redirect on success
    
    # Verify the feed was deleted
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 0


def test_delete_feed_rejects_invalid_csrf_token(client, test_db):
    """Test that deleting a feed rejects an invalid CSRF token."""
    # First, create a feed
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    feeds = Feed.get_all(test_db)
    feed_id = feeds[0].id
    
    # Get a session ID
    home_response = client.get("/")
    session_id = home_response.cookies.get("session_id")
    
    # Try to delete with an invalid CSRF token
    response = client.post(
        f"/feed/{feed_id}/delete",
        data={"csrf_token": "invalid_token_99999"},
        cookies={"session_id": session_id},
        follow_redirects=False,
    )
    assert response.status_code == 403  # Forbidden
    
    # Verify the feed was NOT deleted
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1


def test_delete_feed_rejects_missing_csrf_token(client, test_db):
    """Test that deleting a feed rejects missing CSRF token."""
    # First, create a feed
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    feeds = Feed.get_all(test_db)
    feed_id = feeds[0].id
    
    # Try to delete without a CSRF token
    response = client.post(
        f"/feed/{feed_id}/delete",
        data={},  # No csrf_token
        follow_redirects=False,
    )
    assert response.status_code == 422  # Unprocessable Entity (missing required field)
    
    # Verify the feed was NOT deleted
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1


def test_csrf_token_is_session_specific(client, test_db):
    """Test that CSRF tokens are tied to specific sessions."""
    # Create a feed so we have a token in the page
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    # Get a token for session 1
    response1 = client.get("/")
    session_id_1 = response1.cookies.get("session_id")
    
    import re
    token_match_1 = re.search(r'name="csrf_token" value="([^"]+)"', response1.text)
    assert token_match_1 is not None, "CSRF token not found in response"
    csrf_token_1 = token_match_1.group(1)
    
    # Get a token for session 2 (new client = new session)
    client2 = TestClient(client.app)
    response2 = client2.get("/")
    session_id_2 = response2.cookies.get("session_id")
    
    token_match_2 = re.search(r'name="csrf_token" value="([^"]+)"', response2.text)
    assert token_match_2 is not None, "CSRF token not found in response"
    csrf_token_2 = token_match_2.group(1)
    
    # Session IDs should be different
    assert session_id_1 != session_id_2
    
    # Try to use session 1's token with session 2's session_id
    response = client.post(
        "/feed",
        data={
            "ounces": "3.0",
            "time": "12:00",
            "date": "2025-12-09",
            "timezone": "UTC",
            "csrf_token": csrf_token_1,
        },
        cookies={"session_id": session_id_2},
        follow_redirects=False,
    )
    assert response.status_code == 403  # Should be rejected
