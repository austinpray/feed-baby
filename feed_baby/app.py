"""FastAPI application with CSRF protection."""

import os
import re
import secrets
from decimal import Decimal
from typing import Annotated

from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from feed_baby.feed import Feed


# CSRF Protection using Synchronizer Token Pattern
class CSRFProtection:
    """Simple CSRF protection using synchronizer tokens.
    
    Note: This implementation uses in-memory token storage which is suitable for
    single-process development environments. For production multi-process/multi-server
    deployments, consider using a shared cache like Redis or a database for token storage.
    """
    
    def __init__(self):
        self.tokens = {}
    
    def generate_token(self, session_id: str) -> str:
        """Generate a new CSRF token for a session."""
        token = secrets.token_urlsafe(32)
        self.tokens[session_id] = token
        return token
    
    def validate_token(self, session_id: str, token: str) -> bool:
        """Validate a CSRF token using constant-time comparison."""
        expected = self.tokens.get(session_id)
        return expected is not None and secrets.compare_digest(expected, token)
    
    def cleanup_old_tokens(self, max_tokens: int = 1000) -> None:
        """Remove oldest tokens if the cache grows too large.
        
        This prevents memory leaks in production by limiting the number of stored tokens.
        Note: This uses dictionary insertion order (Python 3.7+) as a simple FIFO strategy.
        For production, consider time-based expiration with explicit timestamps.
        
        Args:
            max_tokens: Maximum number of tokens to keep in memory
        """
        if len(self.tokens) > max_tokens:
            # Remove oldest half of tokens (simple FIFO strategy based on insertion order)
            keys_to_remove = list(self.tokens.keys())[:max_tokens // 2]
            for key in keys_to_remove:
                del self.tokens[key]


csrf_protection = CSRFProtection()


def get_csrf_token(request: Request) -> tuple[str, str]:
    """Get or create CSRF token for the current session.
    
    Returns:
        Tuple of (csrf_token, session_id)
    """
    session_id = request.cookies.get("session_id", "")
    if not session_id:
        session_id = secrets.token_urlsafe(16)
    
    if session_id not in csrf_protection.tokens:
        csrf_protection.generate_token(session_id)
    
    # Perform cleanup periodically to prevent memory leaks
    csrf_protection.cleanup_old_tokens()
    
    return csrf_protection.tokens[session_id], session_id


def validate_csrf_token(
    request: Request,
    csrf_token: Annotated[str, Form()],
) -> None:
    """Validate CSRF token from form submission."""
    session_id = request.cookies.get("session_id", "")
    if not csrf_protection.validate_token(session_id, csrf_token):
        raise HTTPException(status_code=403, detail="CSRF token validation failed")


def bootstrap_server(app: FastAPI, db_path: str) -> None:
    """Bootstrap the FastAPI server with routes and state.
    
    Args:
        app: FastAPI application instance
        db_path: Path to SQLite database
    """
    app.state.db_path = db_path
    
    # Determine if we're in production based on environment
    is_production = os.environ.get("ENVIRONMENT", "development").lower() == "production"
    
    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        """Display home page with feed history."""
        feeds = Feed.get_all(request.app.state.db_path)
        csrf_token, session_id = get_csrf_token(request)
        response = templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "feeds": feeds,
                "csrf_token": csrf_token,
            },
        )
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            samesite="strict",
            secure=is_production,  # Only send over HTTPS in production
        )
        return response

    @app.get("/feed", response_class=HTMLResponse)
    def feed_form(request: Request):
        """Display feed entry form."""
        csrf_token, session_id = get_csrf_token(request)
        response = templates.TemplateResponse(
            "feed_form.html",
            {
                "request": request,
                "csrf_token": csrf_token,
            },
        )
        response.set_cookie(
            "session_id",
            session_id,
            httponly=True,
            samesite="strict",
            secure=is_production,  # Only send over HTTPS in production
        )
        return response

    @app.post("/feed", response_model=None)
    def create_feed(
        request: Request,
        ounces: Annotated[Decimal, Form()],
        time: Annotated[str, Form()],
        date: Annotated[str, Form()],
        timezone: Annotated[str, Form()],
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        """Create a new feed entry."""
        # Validate CSRF token
        validate_csrf_token(request, csrf_token)
        
        feed = Feed.from_form(ounces=ounces, time=time, date=date, timezone=timezone)
        feed.save(request.app.state.db_path)
        return RedirectResponse(url="/", status_code=303)

    @app.post("/feed/{feed_id}/delete", response_model=None)
    def delete_feed(
        request: Request,
        feed_id: int,
        csrf_token: Annotated[str, Form()],
    ) -> RedirectResponse:
        """Delete a feed entry with CSRF protection."""
        # Validate CSRF token - CRITICAL SECURITY FEATURE
        validate_csrf_token(request, csrf_token)
        
        deleted = Feed.delete(feed_id, request.app.state.db_path)
        if not deleted:
            raise HTTPException(status_code=404, detail="Feed not found")
        return RedirectResponse(url="/", status_code=303)
