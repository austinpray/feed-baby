"""Request-scoped session caching to avoid duplicate database queries."""

import sqlite3

from starlette.requests import Request

from feed_baby.db import get_connection


def get_or_fetch_session(request: Request, db_path: str) -> tuple[int, str] | None:
    """Get session data from cache or fetch from DB if not cached.

    This helper ensures that session data is only fetched once per request,
    even if multiple middlewares or dependencies need access to it.

    Args:
        request: The current request
        db_path: Path to the SQLite database

    Returns:
        Tuple of (user_id, csrf_token) if session exists, None otherwise
    """
    if not hasattr(request.state, "_session_cache"):
        session_id = request.cookies.get("session_id")
        if session_id:
            # Fetch session from database
            conn = None
            try:
                conn = get_connection(db_path)
                cursor = conn.execute(
                    "SELECT user_id, csrf_token FROM sessions WHERE id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                request.state._session_cache = (
                    (row["user_id"], row["csrf_token"]) if row else None
                )
            except sqlite3.Error:
                request.state._session_cache = None
            finally:
                if conn:
                    conn.close()
        else:
            request.state._session_cache = None

    return request.state._session_cache
