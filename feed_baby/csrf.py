"""CSRF protection middleware."""

import secrets
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from feed_baby.session_cache import get_or_fetch_session


# HTTP methods that require CSRF protection
CSRF_PROTECTED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# HTTP methods that are safe (read-only, no CSRF needed)
CSRF_SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware that validates CSRF tokens on state-changing requests.

    Uses request-scoped session caching to avoid duplicate database queries.
    Middleware registration order does not matter.

    CSRF protection only applies to:
    - Authenticated requests (those with a valid session)
    - State-changing methods (POST, PUT, PATCH, DELETE)

    The client must send the CSRF token in the X-CSRFToken header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token for state-changing requests."""

        # Skip CSRF check for safe methods
        if request.method in CSRF_SAFE_METHODS:
            return await call_next(request)

        # Get session data using caching helper
        session_data = get_or_fetch_session(request, request.app.state.db_path)

        # Skip CSRF check for unauthenticated requests
        if session_data is None:
            return await call_next(request)

        # For authenticated requests with state-changing methods,
        # validate the CSRF token
        user_id, csrf_token = session_data
        client_token = request.headers.get("x-csrftoken")

        if not client_token:
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing"},
            )

        # Use constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(csrf_token, client_token):
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token invalid"},
            )

        # Token is valid, proceed with request
        return await call_next(request)
