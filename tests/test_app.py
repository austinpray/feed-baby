"""Integration tests for HTTP endpoints."""

from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest


@pytest.fixture
def client(tmp_path):
    """Create test client with temporary database."""
    from migrate import migrate
    from feed_baby.app import bootstrap_server

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    app = FastAPI()
    bootstrap_server(app, db_path)
    return TestClient(app)


def test_get_feeds_new_form(client):
    """Test GET /feeds/new returns feed form."""
    response = client.get("/feeds/new")
    assert response.status_code == 200
    assert b"Log a feed" in response.content


def test_post_feeds_create(client):
    """Test POST /feeds creates new feed."""
    response = client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 200
    assert b"Feed logged" in response.content


def test_delete_feeds_success(client):
    """Test DELETE /feeds/{id} removes feed."""
    # Create a feed first
    client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
    )

    # Delete the feed (feed_id is 1 since it's the first feed)
    # Use follow_redirects=False to check redirect status code
    response = client.delete("/feeds/1", follow_redirects=False)

    # Should redirect with 303 to /feeds
    assert response.status_code == 303
    assert response.headers["location"] == "/feeds"


def test_delete_feeds_not_found(client):
    """Test DELETE /feeds/{id} returns error for non-existent feed."""
    response = client.delete("/feeds/9999")
    assert response.status_code == 200  # Returns error template
    assert b"Feed with ID 9999 not found" in response.content
