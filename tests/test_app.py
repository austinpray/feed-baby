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


@pytest.fixture
def authenticated_client(tmp_path):
    """Create test client with authenticated user."""
    from migrate import migrate
    from feed_baby.app import bootstrap_server
    from feed_baby.user import User

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create test user
    user = User.create(username="testuser", password="testpass", db_path=db_path)
    assert user is not None

    app = FastAPI()
    bootstrap_server(app, db_path)
    client = TestClient(app)

    # Log in and capture session cookie
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "testpass"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    return client


def test_get_feeds_new_form(client):
    """Test GET /feeds/new returns feed form."""
    response = client.get("/feeds/new")
    assert response.status_code == 200
    assert b"Log a feed" in response.content


def test_post_feeds_create(authenticated_client):
    """Test POST /feeds creates new feed when authenticated."""
    response = authenticated_client.post(
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


def test_post_feeds_requires_auth(client):
    """Test POST /feeds redirects to login when not authenticated."""
    response = client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_delete_feeds_success(authenticated_client):
    """Test DELETE /feeds/{id} removes feed when authenticated."""
    # Create a feed first
    authenticated_client.post(
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
    response = authenticated_client.delete("/feeds/1", follow_redirects=False)

    # Should redirect with 303 to /feeds
    assert response.status_code == 303
    assert response.headers["location"] == "/feeds"


def test_delete_feeds_requires_auth(client):
    """Test DELETE /feeds/{id} redirects to login when not authenticated."""
    response = client.delete("/feeds/1", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_delete_feeds_not_found(authenticated_client):
    """Test DELETE /feeds/{id} returns error for non-existent feed."""
    response = authenticated_client.delete("/feeds/9999")
    assert response.status_code == 200  # Returns error template
    assert b"Feed with ID 9999 not found" in response.content


def test_register_success(client):
    """Test POST /register creates a new user and redirects."""
    response = client.post(
        "/register",
        data={"username": "newuser", "password": "newpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session_id" in response.cookies


def test_register_duplicate_username(client):
    """Test POST /register fails with duplicate username."""
    # Register first user
    client.post("/register", data={"username": "duplicateuser", "password": "password1"})

    # Try to register with same username
    response = client.post(
        "/register", data={"username": "duplicateuser", "password": "password2"}
    )
    assert response.status_code == 200
    assert b"Username already exists" in response.content


def test_login_success(client):
    """Test POST /login authenticates user and redirects."""
    # Register a user first
    client.post(
        "/register",
        data={"username": "loginuser", "password": "loginpassword"},
        follow_redirects=False,
    )

    # Clear the session cookie set by registration
    client.cookies.clear()

    # Login
    response = client.post(
        "/login",
        data={"username": "loginuser", "password": "loginpassword"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    assert "session_id" in response.cookies


def test_login_invalid_credentials(client):
    """Test POST /login fails with invalid credentials."""
    response = client.post(
        "/login", data={"username": "nonexistent", "password": "wrongpassword"}
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.content


def test_logout(authenticated_client):
    """Test POST /logout clears session."""
    response = authenticated_client.post("/logout", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    # Note: TestClient doesn't actually delete cookies, so we can't verify deletion
