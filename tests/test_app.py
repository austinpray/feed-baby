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
    """Create test client with authenticated user and CSRF token."""
    from migrate import migrate
    from feed_baby.app import bootstrap_server
    from feed_baby.user import User
    from feed_baby.auth import get_session

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

    # Extract CSRF token from session
    session_id = client.cookies.get("session_id")
    assert session_id is not None
    session_data = get_session(session_id, db_path)
    assert session_data is not None
    csrf_token = session_data[1]

    # Attach CSRF token to client for convenience
    client.csrf_token = csrf_token  # type: ignore[attr-defined]

    return client


def test_get_feeds_new_requires_auth(client):
    """Test GET /feeds/new redirects to login when unauthenticated."""
    response = client.get("/feeds/new", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=feeds_new"


def test_get_feeds_new_form_authenticated(authenticated_client):
    """Test GET /feeds/new returns feed form when authenticated."""
    response = authenticated_client.get("/feeds/new")
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
        headers={"X-CSRFToken": authenticated_client.csrf_token},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


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
    assert response.headers["location"] == "/login?next=feeds_new"


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
        headers={"X-CSRFToken": authenticated_client.csrf_token},
    )

    # Delete the feed (feed_id is 1 since it's the first feed)
    # Use follow_redirects=False to check redirect status code
    response = authenticated_client.delete(
        "/feeds/1",
        follow_redirects=False,
        headers={"X-CSRFToken": authenticated_client.csrf_token},
    )

    # Should redirect with 303 to /feeds
    assert response.status_code == 303
    assert response.headers["location"] == "/feeds"


def test_delete_feeds_requires_auth(client):
    """Test DELETE /feeds/{id} redirects to login when not authenticated."""
    response = client.delete("/feeds/1", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=feeds_list"


def test_login_next_param_redirect(client):
    """Test that login honors next parameter and redirects safely using tokens."""
    # Register a user first
    client.post(
        "/register",
        data={"username": "loginuser2", "password": "loginpassword2"},
        follow_redirects=False,
    )

    # Clear auto-login cookie from registration
    client.cookies.clear()

    # Request login page with next token
    get_resp = client.get("/login?next=feeds_new")
    assert get_resp.status_code == 200
    assert b"name=\"next\"" in get_resp.content

    # Post login with valid token, expect redirect to mapped path
    post_resp = client.post(
        "/login",
        data={"username": "loginuser2", "password": "loginpassword2", "next": "feeds_new"},
        follow_redirects=False,
    )
    assert post_resp.status_code == 303
    assert post_resp.headers["location"] == "/feeds/new"

    # Ensure invalid token is rejected (redirects to / home)
    client.cookies.clear()
    post_resp2 = client.post(
        "/login",
        data={"username": "loginuser2", "password": "loginpassword2", "next": "invalid_token"},
        follow_redirects=False,
    )
    assert post_resp2.status_code == 303
    assert post_resp2.headers["location"] == "/"

    # Ensure URL path is rejected (not a valid token)
    client.cookies.clear()
    post_resp3 = client.post(
        "/login",
        data={"username": "loginuser2", "password": "loginpassword2", "next": "/feeds/new"},
        follow_redirects=False,
    )
    assert post_resp3.status_code == 303
    assert post_resp3.headers["location"] == "/"

    # Ensure external URL is rejected (not a valid token)
    client.cookies.clear()
    post_resp4 = client.post(
        "/login",
        data={"username": "loginuser2", "password": "loginpassword2", "next": "https://evil.com"},
        follow_redirects=False,
    )
    assert post_resp4.status_code == 303
    assert post_resp4.headers["location"] == "/"


def test_delete_feeds_not_found(authenticated_client):
    """Test DELETE /feeds/{id} returns error for non-existent feed."""
    response = authenticated_client.delete(
        "/feeds/9999",
        headers={"X-CSRFToken": authenticated_client.csrf_token},
    )
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
    from feed_baby.auth import get_session

    # Register first user
    first_response = client.post(
        "/register",
        data={"username": "duplicateuser", "password": "password1"},
        follow_redirects=False,
    )
    assert first_response.status_code == 303

    # Get CSRF token from the session created by first registration
    session_id = client.cookies.get("session_id")
    session_data = get_session(session_id, client.app.state.db_path)
    csrf_token = session_data[1] if session_data else None

    # Try to register with same username (need CSRF token since we're now authenticated)
    response = client.post(
        "/register",
        data={"username": "duplicateuser", "password": "password2"},
        headers={"X-CSRFToken": csrf_token} if csrf_token else {},
    )
    assert response.status_code == 409
    assert response.json()["error"] == "Username already exists"


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
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid username or password"


def test_login_empty_username(client):
    """Test POST /login returns 422 for empty username (validation error)."""
    response = client.post("/login", data={"username": "", "password": "somepassword"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "username"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_login_empty_password(client):
    """Test POST /login returns 422 for empty password (validation error)."""
    response = client.post("/login", data={"username": "someuser", "password": ""})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_login_empty_username_and_password(client):
    """Test POST /login returns 422 for both username and password empty."""
    response = client.post("/login", data={"username": "", "password": ""})
    assert response.status_code == 422
    # Should have errors for both fields
    error_locs = [error["loc"] for error in response.json()["detail"]]
    assert ["body", "username"] in error_locs
    assert ["body", "password"] in error_locs


def test_login_missing_username(client):
    """Test POST /login returns 422 when username field is missing."""
    response = client.post("/login", data={"password": "somepassword"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "username"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_login_missing_password(client):
    """Test POST /login returns 422 when password field is missing."""
    response = client.post("/login", data={"username": "someuser"})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "password"]
    assert response.json()["detail"][0]["type"] == "missing"


def test_login_whitespace_only_username(client):
    """Test POST /login handles whitespace-only username gracefully."""
    # Whitespace-only username will pass validation but fail authentication
    response = client.post("/login", data={"username": "   ", "password": "somepassword"})
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid username or password"


def test_login_whitespace_only_password(client):
    """Test POST /login handles whitespace-only password gracefully."""
    # Register a user first so username exists
    client.post(
        "/register",
        data={"username": "testwhitespace", "password": "validpassword"},
        follow_redirects=False,
    )
    client.cookies.clear()

    # Try logging in with whitespace-only password
    response = client.post(
        "/login", data={"username": "testwhitespace", "password": "   "}
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid username or password"


def test_logout(authenticated_client):
    """Test POST /logout clears session."""
    response = authenticated_client.post(
        "/logout",
        follow_redirects=False,
        headers={"X-CSRFToken": authenticated_client.csrf_token},
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"
    # Note: TestClient doesn't actually delete cookies, so we can't verify deletion
