"""Tests for CSRF protection middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
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
def authenticated_client_with_token(tmp_path):
    """Create test client with authenticated user and extract CSRF token."""
    from migrate import migrate
    from feed_baby.app import bootstrap_server
    from feed_baby.user import User
    from feed_baby.auth import get_session

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create test user
    user = User.create(username="testuser", password="testpass", db_path=db_path)
    assert user is not None
    assert user.id is not None

    app = FastAPI()
    bootstrap_server(app, db_path)
    client = TestClient(app)

    # Login to get session cookie
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

    return client, csrf_token


def test_csrf_token_in_meta_tag(authenticated_client_with_token):
    """Test that CSRF token appears in meta tag for authenticated users."""
    client, csrf_token = authenticated_client_with_token

    response = client.get("/feeds/new")
    assert response.status_code == 200
    assert b'<meta name="csrf-token"' in response.content
    assert csrf_token.encode() in response.content


def test_csrf_token_not_in_meta_tag_unauthenticated(client):
    """Test that CSRF token does not appear for unauthenticated users."""
    response = client.get("/")
    assert response.status_code == 200
    assert b'<meta name="csrf-token"' not in response.content


def test_csrf_post_without_token_fails(authenticated_client_with_token):
    """Test that POST without CSRF token is rejected."""
    client, _ = authenticated_client_with_token

    # Try to create feed without CSRF token
    response = client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


def test_csrf_post_with_valid_token_succeeds(authenticated_client_with_token):
    """Test that POST with valid CSRF token succeeds."""
    client, csrf_token = authenticated_client_with_token

    response = client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
        headers={"X-CSRFToken": csrf_token},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_csrf_post_with_invalid_token_fails(authenticated_client_with_token):
    """Test that POST with invalid CSRF token is rejected."""
    client, _ = authenticated_client_with_token

    response = client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
        headers={"X-CSRFToken": "invalid-token-12345"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token invalid"


def test_csrf_delete_without_token_fails(authenticated_client_with_token):
    """Test that DELETE without CSRF token is rejected."""
    client, csrf_token = authenticated_client_with_token

    # Create a feed first (with CSRF token)
    client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
        headers={"X-CSRFToken": csrf_token},
    )

    # Try to delete without CSRF token
    response = client.delete("/feeds/1")
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


def test_csrf_delete_with_valid_token_succeeds(authenticated_client_with_token):
    """Test that DELETE with valid CSRF token succeeds."""
    client, csrf_token = authenticated_client_with_token

    # Create a feed first
    client.post(
        "/feeds",
        data={
            "ounces": "3.5",
            "time": "14:30",
            "date": "2025-12-09",
            "timezone": "UTC",
        },
        headers={"X-CSRFToken": csrf_token},
    )

    # Delete with valid token
    response = client.delete(
        "/feeds/1",
        headers={"X-CSRFToken": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/feeds"


def test_csrf_get_requests_not_protected(authenticated_client_with_token):
    """Test that GET requests don't require CSRF token."""
    client, _ = authenticated_client_with_token

    # GET requests should work without CSRF token
    response = client.get("/feeds/new")
    assert response.status_code == 200


def test_csrf_unauthenticated_post_not_protected(client):
    """Test that unauthenticated POST requests don't require CSRF token."""
    # Login and register endpoints should work without CSRF token
    # since the user doesn't have a session yet

    response = client.post(
        "/register",
        data={"username": "newuser", "password": "newpass"},
        follow_redirects=False,
    )
    # Should succeed (redirects to /)
    assert response.status_code == 303


def test_csrf_logout_without_token_fails(authenticated_client_with_token):
    """Test that logout without CSRF token is rejected."""
    client, _ = authenticated_client_with_token

    response = client.post("/logout")
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"


def test_csrf_logout_with_valid_token_succeeds(authenticated_client_with_token):
    """Test that logout with valid CSRF token succeeds."""
    client, csrf_token = authenticated_client_with_token

    response = client.post(
        "/logout",
        headers={"X-CSRFToken": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_middleware_order_independence(tmp_path):
    """Test that middleware works regardless of registration order."""
    from migrate import migrate
    from feed_baby.user import User
    from feed_baby.auth import AuthMiddleware
    from feed_baby.csrf import CSRFMiddleware
    from starlette.requests import Request

    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create test user
    user = User.create(username="testuser", password="testpass", db_path=db_path)
    assert user is not None

    # Test with REVERSE middleware order (Auth before CSRF)
    app = FastAPI()
    app.state.db_path = db_path
    app.state.secure_cookies = False

    # Register in OPPOSITE order: Auth first, then CSRF
    # (In normal app, CSRF is registered first)
    app.add_middleware(AuthMiddleware)  # type: ignore[arg-type]
    app.add_middleware(CSRFMiddleware)  # type: ignore[arg-type]

    # Add a test endpoint that requires CSRF protection
    @app.post("/test")
    def test_endpoint(request: Request):
        return {"success": True}

    client = TestClient(app)

    # Log in to get session cookie
    from feed_baby.auth import create_session

    assert user.id is not None
    session_id, csrf_token = create_session(user.id, db_path)

    # Set session cookie manually
    client.cookies.set("session_id", session_id)

    # Try POST without CSRF token - should fail with 403
    response = client.post("/test")
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing"

    # Try POST with valid CSRF token - should succeed
    response = client.post("/test", headers={"X-CSRFToken": csrf_token})
    assert response.status_code == 200
    assert response.json()["success"] is True
