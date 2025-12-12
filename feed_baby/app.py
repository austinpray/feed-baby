from typing import Annotated
from decimal import Decimal
import math
import logging

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from icalendar import Calendar, Event, vDatetime

from feed_baby.feed import Feed
from feed_baby.user import User
from feed_baby.auth import AuthMiddleware, create_session, delete_session, SessionCreationError

logger = logging.getLogger(__name__)

# Valid redirect targets after login - maps token to URL path
REDIRECT_TARGETS = {
    "feeds_new": "/feeds/new",
    "feeds_list": "/feeds",
    "home": "/",
}


def bootstrap_server(app: FastAPI, db_path: str) -> FastAPI:
    # Store db_path in app state for routes to access
    app.state.db_path = db_path

    # Add authentication middleware
    # Note: type: ignore[arg-type] is needed due to a known issue with Starlette's
    # middleware typing in the ty type checker. See:
    # https://github.com/astral-sh/ty/issues/1635
    app.add_middleware(AuthMiddleware)  # type: ignore[arg-type]

    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    def read_root(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        # Show only the 8 most recent feeds on homepage
        feeds = Feed.get_all(request.app.state.db_path, limit=8, offset=0)
        user = getattr(request.state, "user", None)

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "feeds": feeds,
                "user": user,
            },
        )

    @app.get("/feeds", response_class=HTMLResponse)
    def list_feeds(request: Request, page: int = 1) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        page = max(1, page)  # Ensure page is at least 1
        limit = 50
        offset = (page - 1) * limit

        feeds = Feed.get_all(request.app.state.db_path, limit=limit, offset=offset)
        total_feeds = Feed.count(request.app.state.db_path)
        total_pages = math.ceil(total_feeds / limit) if total_feeds > 0 else 1
        user = getattr(request.state, "user", None)

        return templates.TemplateResponse(
            request=request,
            name="feeds.html",
            context={
                "feeds": feeds,
                "page": page,
                "total_pages": total_pages,
                "total_feeds": total_feeds,
                "user": user,
            },
        )

    @app.get("/feeds.ics")
    def feeds_calendar(request: Request):  # pyright: ignore[reportUnusedFunction]
        cal = Calendar()
        cal.add("prodid", "-//feed-baby//austinpray.com//")
        cal.add("version", "2.0")

        feeds = Feed.get_all(request.app.state.db_path)
        for feed in feeds:
            event = Event()
            event.add("summary", "Feed")
            event.add("dtstart", vDatetime(feed.datetime))
            event.add("dtend", vDatetime(feed.datetime.add(hours=1)))
            event.add("description", "Feed the baby")
            cal.add_component(event)

        ical_data = cal.to_ical().decode("utf-8")

        return Response(content=ical_data, media_type="text/calendar")

    @app.get("/feeds/new", response_class=HTMLResponse)
    def new_feed(request: Request) -> HTMLResponse | RedirectResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, "user", None)
        if not user:
            return RedirectResponse(url="/login?next=feeds_new", status_code=303)
        return templates.TemplateResponse(
            request=request, name="feed.html", context={"user": user}
        )

    @app.post("/feeds", response_model=None)
    def create_feed(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        ounces: Annotated[Decimal, Form()],
        time: Annotated[str, Form()],
        date: Annotated[str, Form()],
        timezone: Annotated[str, Form()],
    ) -> Response:
        # Require authentication for creating feeds
        user = getattr(request.state, "user", None)
        if not user:
            return RedirectResponse(url="/login?next=feeds_new", status_code=303)

        feed = Feed.from_form(
            ounces=ounces, time=time, date=date, timezone=timezone, user_id=user.id
        )
        feed.save(request.app.state.db_path, user.id)

        summary = f"Logged {feed.ounces}oz from {feed.datetime.to_day_datetime_string()} ({feed.datetime.timezone}) ({feed.datetime.diff_for_humans()})"
        return templates.TemplateResponse(
            request=request, context={"summary": summary, "user": user}, name="feed_post.html"
        )

    @app.delete("/feeds/{feed_id}", response_model=None)
    def delete_feed(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        feed_id: int,
    ) -> Response:
        # Require authentication for deleting feeds
        user = getattr(request.state, "user", None)
        if not user:
            return RedirectResponse(url="/login?next=feeds_list", status_code=303)

        deleted = Feed.delete(feed_id, request.app.state.db_path)

        if not deleted:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": f"Feed with ID {feed_id} not found",
                    "back_link": "/feeds",
                    "user": user,
                },
            )

        # Redirect to feeds page after successful deletion
        return RedirectResponse(url="/feeds", status_code=303)

    # Authentication routes
    @app.get("/register", response_class=HTMLResponse)
    def get_register(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, "user", None)
        return templates.TemplateResponse(
            request=request, name="register.html", context={"user": user}
        )

    @app.post("/register", response_model=None)
    def post_register(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ) -> Response:
        user = User.create(
            username=username, password=password, db_path=request.app.state.db_path
        )
        if not user:
            return templates.TemplateResponse(
                request=request,
                name="register.html",
                context={"error": "Username already exists", "user": None},
            )

        # Auto-login after registration
        assert user.id is not None  # User was just created, so ID is guaranteed
        try:
            session_id = create_session(user.id, request.app.state.db_path)
        except Exception:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": "Failed to create session. Please try again.",
                    "back_link": "/register",
                    "user": None,
                },
                status_code=500,
            )
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response

    @app.get("/login", response_class=HTMLResponse)
    def get_login(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, "user", None)
        next_param = request.query_params.get("next")
        return templates.TemplateResponse(
            request=request, name="login.html", context={"user": user, "next": next_param}
        )

    @app.post("/login", response_model=None)
    def post_login(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
        next: Annotated[str | None, Form()] = None,
    ) -> Response:
        user = User.authenticate(
            username=username, password=password, db_path=request.app.state.db_path
        )
        if not user:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Invalid username or password", "user": None, "next": next},
            )

        assert user.id is not None  # User was authenticated, so ID is guaranteed
        try:
            session_id = create_session(user.id, request.app.state.db_path)
        except SessionCreationError as e:
            logger.error("Session creation failed for user %s: %s", user.id, e)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": "Failed to create session. Please try again.",
                    "back_link": "/login",
                    "user": None,
                },
                status_code=500,
            )
        # Determine safe redirect target using server-side mapping
        redirect_target = REDIRECT_TARGETS.get(next or "", "/")
        response = RedirectResponse(url=redirect_target, status_code=303)
        response.set_cookie(key="session_id", value=session_id, httponly=True)
        return response

    @app.post("/logout")
    def post_logout(request: Request) -> RedirectResponse:  # pyright: ignore[reportUnusedFunction]
        session_id = request.cookies.get("session_id")
        if session_id:
            delete_session(session_id, request.app.state.db_path)

        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(key="session_id")
        return response

    return app
