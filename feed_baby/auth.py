"""Authentication middleware and session management."""

import secrets
import sqlite3
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from feed_baby.db import get_connection
from feed_baby.user import User
from feed_baby.session_cache import get_or_fetch_session


class SessionCreationError(Exception):
    """Raised when session creation fails."""

    pass


def create_session(user_id: int, db_path: str) -> tuple[str, str]:
    """Create a new session for a user.

    Args:
        user_id: The user's database ID
        db_path: Path to the SQLite database

    Returns:
        Tuple of (session_id, csrf_token)

    Raises:
        SessionCreationError: If session creation fails in database
    """
    session_id = str(uuid.uuid4())
    csrf_token = secrets.token_urlsafe(32)
    conn = None
    try:
        conn = get_connection(db_path)
        with conn:
            conn.execute(
                "INSERT INTO sessions (id, user_id, csrf_token) VALUES (?, ?, ?)",
                (session_id, user_id, csrf_token),
            )
    except sqlite3.Error as e:
        raise SessionCreationError(f"Failed to create session: {e}") from e
    finally:
        if conn:
            conn.close()
    return session_id, csrf_token


def get_session(session_id: str, db_path: str) -> tuple[int, str] | None:
    """Get the user ID and CSRF token for a session ID.

    Args:
        session_id: Session ID to look up
        db_path: Path to the SQLite database

    Returns:
        Tuple of (user_id, csrf_token) if session exists, None otherwise
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT user_id, csrf_token FROM sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        return (row["user_id"], row["csrf_token"]) if row else None
    except sqlite3.Error:
        return None
    finally:
        if conn:
            conn.close()


def delete_session(session_id: str, db_path: str) -> None:
    """Delete a session.

    Args:
        session_id: Session ID to delete
        db_path: Path to the SQLite database
    """
    conn = None
    try:
        conn = get_connection(db_path)
        with conn:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    except sqlite3.Error:
        # Silently ignore errors on delete
        pass
    finally:
        if conn:
            conn.close()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that loads user from session cookie.

    This middleware reads the session_id cookie on every request, looks up the user,
    and attaches it to request.state.user. If no valid session exists, sets user to None.

    Uses request-scoped session caching to avoid duplicate DB queries.
    Middleware registration order does not matter.

    This middleware does NOT block requests - authentication enforcement happens in routes.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Load user and CSRF token from session and attach to request state."""
        request.state.user = None
        request.state.csrf_token = None

        # Use caching helper instead of direct get_session call
        session_data = get_or_fetch_session(request, request.app.state.db_path)
        if session_data is not None:
            user_id, csrf_token = session_data
            user = User.get_by_id(user_id, request.app.state.db_path)
            request.state.user = user
            request.state.csrf_token = csrf_token

        response = await call_next(request)
        return response
