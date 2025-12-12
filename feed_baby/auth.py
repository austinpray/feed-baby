"""Authentication middleware and session management."""

import sqlite3
import uuid
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from feed_baby.db import get_connection
from feed_baby.user import User


class SessionCreationError(Exception):
    """Raised when session creation fails."""

    pass


def create_session(user_id: int, db_path: str) -> str:
    """Create a new session for a user.

    Args:
        user_id: The user's database ID
        db_path: Path to the SQLite database

    Returns:
        Session ID (UUID4 string)

    Raises:
        SessionCreationError: If session creation fails in database
    """
    session_id = str(uuid.uuid4())
    conn = None
    try:
        conn = get_connection(db_path)
        with conn:
            conn.execute(
                "INSERT INTO sessions (id, user_id) VALUES (?, ?)",
                (session_id, user_id),
            )
    except sqlite3.Error as e:
        raise SessionCreationError(f"Failed to create session: {e}") from e
    finally:
        if conn:
            conn.close()
    return session_id


def get_session(session_id: str, db_path: str) -> int | None:
    """Get the user ID for a session ID.

    Args:
        session_id: Session ID to look up
        db_path: Path to the SQLite database

    Returns:
        User ID if session exists, None otherwise
    """
    conn = None
    try:
        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT user_id FROM sessions WHERE id = ?", (session_id,)
        )
        row = cursor.fetchone()
        return row["user_id"] if row else None
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

    This middleware does NOT block requests - authentication enforcement happens in routes.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Load user from session and attach to request state."""
        request.state.user = None

        session_id = request.cookies.get("session_id")
        if session_id:
            user_id = get_session(session_id, request.app.state.db_path)
            if user_id is not None:
                user = User.get_by_id(user_id, request.app.state.db_path)
                request.state.user = user

        response = await call_next(request)
        return response
