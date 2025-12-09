from typing import Annotated
from decimal import Decimal

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from feed_baby.feed import Feed
from feed_baby.user import User
from feed_baby.auth import AuthMiddleware, create_session, delete_session


def bootstrap_server(app: FastAPI, db_path: str) -> FastAPI:
    # Store db_path in app state for routes to access
    app.state.db_path = db_path

    # Add authentication middleware
    app.add_middleware(AuthMiddleware)

    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    def read_root(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        feeds = Feed.get_all(request.app.state.db_path)
        user = getattr(request.state, 'user', None)
        return templates.TemplateResponse(
            request=request, name="index.html", context={"feeds": feeds, "user": user}
        )

    @app.get("/feeds/new", response_class=HTMLResponse)
    def new_feed(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, 'user', None)
        return templates.TemplateResponse(request=request, name="feed.html", context={"user": user})

    @app.post("/feeds", response_model=None)
    def create_feed(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        ounces: Annotated[Decimal, Form()],
        time: Annotated[str, Form()],
        date: Annotated[str, Form()],
        timezone: Annotated[str, Form()],
    ) -> Response:
        # Require authentication for modifying feeds
        user = getattr(request.state, 'user', None)
        if user is None:
            return RedirectResponse(url="/login", status_code=303)

        feed = Feed.from_form(ounces=ounces, time=time, date=date, timezone=timezone)
        feed.save(request.app.state.db_path, user_id=user.id)

        summary = f"Logged {feed.ounces}oz from {feed.datetime.to_day_datetime_string()} ({feed.datetime.timezone}) ({feed.datetime.diff_for_humans()})"
        return templates.TemplateResponse(
            request=request, context={"summary": summary, "user": user}, name="feed_post.html"
        )

    @app.delete("/feeds/{feed_id}", response_model=None)
    def delete_feed(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        feed_id: int,
    ) -> Response:
        # Require authentication for modifying feeds
        user = getattr(request.state, 'user', None)
        if user is None:
            return RedirectResponse(url="/login", status_code=303)

        deleted = Feed.delete(feed_id, request.app.state.db_path)

        if not deleted:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": f"Feed with ID {feed_id} not found",
                    "back_link": "/",
                    "user": user
                }
            )

        # Redirect to home page after successful deletion
        return RedirectResponse(url="/", status_code=303)

    # Authentication routes
    @app.get("/register", response_class=HTMLResponse)
    def register_form(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, 'user', None)
        return templates.TemplateResponse(request=request, name="register.html", context={"user": user})

    @app.post("/register", response_model=None)
    def register(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ) -> Response:
        user = User.create(username=username, password=password, db_path=request.app.state.db_path)
        if user is None:
            return templates.TemplateResponse(
                request=request,
                name="register.html",
                context={"error": "Username already exists", "user": None}
            )

        # Auto-login after registration
        session_token = create_session(user.id)  # pyright: ignore[reportArgumentType]
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value=session_token, httponly=True)
        return response

    @app.get("/login", response_class=HTMLResponse)
    def login_form(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        user = getattr(request.state, 'user', None)
        return templates.TemplateResponse(request=request, name="login.html", context={"user": user})

    @app.post("/login", response_model=None)
    def login(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        username: Annotated[str, Form()],
        password: Annotated[str, Form()],
    ) -> Response:
        user = User.authenticate(username=username, password=password, db_path=request.app.state.db_path)
        if user is None:
            return templates.TemplateResponse(
                request=request,
                name="login.html",
                context={"error": "Invalid username or password", "user": None}
            )

        session_token = create_session(user.id)  # pyright: ignore[reportArgumentType]
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value=session_token, httponly=True)
        return response

    @app.post("/logout")
    def logout(request: Request) -> RedirectResponse:  # pyright: ignore[reportUnusedFunction]
        session_token = request.cookies.get("session")
        if session_token:
            delete_session(session_token)

        response = RedirectResponse(url="/", status_code=303)
        response.delete_cookie(key="session")
        return response

    return app
