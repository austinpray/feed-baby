from typing import Annotated
from decimal import Decimal
import math

from fastapi import FastAPI, Request, Form, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from icalendar import Calendar, Event, vDatetime

from feed_baby.feed import Feed


def bootstrap_server(app: FastAPI, db_path: str) -> FastAPI:
    # Store db_path in app state for routes to access
    app.state.db_path = db_path

    templates = Jinja2Templates(directory="templates")

    @app.get("/", response_class=HTMLResponse)
    def read_root(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        # Show only the 8 most recent feeds on homepage
        feeds = Feed.get_all(request.app.state.db_path, limit=8, offset=0)
        
        return templates.TemplateResponse(
            request=request, 
            name="index.html", 
            context={
                "feeds": feeds,
            }
        )

    @app.get("/feeds", response_class=HTMLResponse)
    def list_feeds(request: Request, page: int = 1) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        page = max(1, page)  # Ensure page is at least 1
        limit = 50
        offset = (page - 1) * limit
        
        feeds = Feed.get_all(request.app.state.db_path, limit=limit, offset=offset)
        total_feeds = Feed.count(request.app.state.db_path)
        total_pages = math.ceil(total_feeds / limit) if total_feeds > 0 else 1
        
        return templates.TemplateResponse(
            request=request, 
            name="feeds.html", 
            context={
                "feeds": feeds,
                "page": page,
                "total_pages": total_pages,
                "total_feeds": total_feeds,
            }
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
    def new_feed(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        return templates.TemplateResponse(request=request, name="feed.html")

    @app.post("/feeds", response_class=HTMLResponse)
    def create_feed(  # pyright: ignore[reportUnusedFunction]
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
                    "back_link": "/feeds"
                }
            )

        # Redirect to feeds page after successful deletion
        return RedirectResponse(url="/feeds", status_code=303)

    return app
