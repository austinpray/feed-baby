"""Authentication middleware and session management."""

import secrets
from typing import Callable
from functools import wraps

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, RedirectResponse

from feed_baby.user import User


# Simple in-memory session store (in production, use Redis or database)
_sessions: dict[str, int] = {}  # session_token -> user_id


def create_session(user_id: int) -> str:
    """Create a new session for a user.
    
    Args:
        user_id: The user's database ID
    
    Returns:
        Session token
    """
    token = secrets.token_urlsafe(32)
    _sessions[token] = user_id
    return token


def get_session_user_id(token: str) -> int | None:
    """Get the user ID for a session token.
    
    Args:
        token: Session token
    
    Returns:
        User ID if session exists, None otherwise
    """
    return _sessions.get(token)


def delete_session(token: str) -> None:
    """Delete a session.
    
    Args:
        token: Session token to delete
    """
    _sessions.pop(token, None)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that loads user from session cookie."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Load user from session and attach to request state."""
        request.state.user = None
        
        session_token = request.cookies.get("session")
        if session_token:
            user_id = get_session_user_id(session_token)
            if user_id is not None:
                user = User.get_by_id(user_id, request.app.state.db_path)
                request.state.user = user
        
        response = await call_next(request)
        return response


def require_auth(func: Callable) -> Callable:
    """Decorator to require authentication for a route.
    
    Redirects to login page if user is not authenticated.
    """
    @wraps(func)
    def wrapper(request: Request, *args, **kwargs):
        if not hasattr(request.state, 'user') or request.state.user is None:
            return RedirectResponse(url="/login", status_code=303)
        return func(request, *args, **kwargs)
    return wrapper
