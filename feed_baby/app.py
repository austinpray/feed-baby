from typing import Annotated
from decimal import Decimal

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from feed_baby.feed import Feed


def bootstrap_server(app: FastAPI, db_path: str) -> FastAPI:
    # Store db_path in app state for routes to access
    app.state.db_path = db_path

    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    def read_root(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        feeds = Feed.get_all(request.app.state.db_path)
        return templates.TemplateResponse(
            request=request, name="index.html", context={"feeds": feeds}
        )

    @app.get("/feeds/new", response_class=HTMLResponse)
    def new_feed(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        return templates.TemplateResponse(request=request, name="feed.html")

    @app.post("/feeds", response_class=HTMLResponse)
    def create_feed( # pyright: ignore[reportUnusedFunction]
        request: Request,
        ounces: Annotated[Decimal, Form()],
        time: Annotated[str, Form()],
        date: Annotated[str, Form()],
        timezone: Annotated[str, Form()],
    ) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        feed = Feed.from_form(ounces=ounces, time=time, date=date, timezone=timezone)
        feed.save(request.app.state.db_path)

        summary = f"Logged {feed.ounces}oz from {feed.datetime.to_day_datetime_string()} ({feed.datetime.timezone}) ({feed.datetime.diff_for_humans()})"
        return templates.TemplateResponse(
            request=request, context={"summary": summary}, name="feed_post.html"
        )

    @app.delete("/feeds/{feed_id}", response_model=None)
    def delete_feed(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        feed_id: int,
    ):
        deleted = Feed.delete(feed_id, request.app.state.db_path)

        if not deleted:
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": f"Feed with ID {feed_id} not found",
                    "back_link": "/"
                }
            )

        # Redirect to home page after successful deletion
        return RedirectResponse(url="/", status_code=303)

    return app
