from typing import Annotated
from decimal import Decimal

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, ValidationError, field_validator
import pendulum

from feed_baby.feed import Feed


class FeedForm(BaseModel):
    """Pydantic model for feed form validation."""

    ounces: Decimal = Field(gt=0, le=10, description="Ounces must be greater than 0 and less than or equal to 10")
    time: str = Field(pattern=r'^\d{2}:\d{2}$', description="Time must be in HH:mm format")
    date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$', description="Date must be in YYYY-MM-DD format")
    timezone: str = Field(min_length=1, description="Timezone is required")

    @field_validator('timezone')
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate that timezone is a valid IANA timezone identifier."""
        try:
            # Try to create a timezone object to validate
            pendulum.timezone(v)
            return v
        except (ValueError, KeyError) as e:
            # pendulum raises ValueError or KeyError for invalid timezones
            raise ValueError(f"Invalid timezone '{v}': {str(e)}")


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

    @app.get("/feed", response_class=HTMLResponse)
    def input_feed(request: Request) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        return templates.TemplateResponse(request=request, name="feed.html")

    @app.post("/feed", response_class=HTMLResponse)
    def create_feed( # pyright: ignore[reportUnusedFunction]
        request: Request,
        ounces: Annotated[Decimal, Form()],
        time: Annotated[str, Form()],
        date: Annotated[str, Form()],
        timezone: Annotated[str, Form()],
    ) -> HTMLResponse:  # pyright: ignore[reportUnusedFunction]
        try:
            # Validate form data using Pydantic
            form_data = FeedForm(ounces=ounces, time=time, date=date, timezone=timezone)

            # Create feed from validated data
            feed = Feed.from_form(
                ounces=form_data.ounces,
                time=form_data.time,
                date=form_data.date,
                timezone=form_data.timezone
            )
            feed.save(request.app.state.db_path)

            summary = f"Logged {feed.ounces}oz from {feed.datetime.to_day_datetime_string()} ({feed.datetime.timezone}) ({feed.datetime.diff_for_humans()})"
            return templates.TemplateResponse(
                request=request, context={"summary": summary}, name="feed_post.html"
            )
        except ValidationError as e:
            # Handle Pydantic validation errors
            error_details = []
            for error in e.errors():
                field = error.get('loc', [''])[0]
                msg = error.get('msg', '')
                error_details.append(f"{field}: {msg}")
            error_msg = "; ".join(error_details)

            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": f"Invalid form data: {error_msg}",
                    "back_link": "/feed"
                },
                status_code=400
            )
        except Exception as e:
            # Handle other errors (e.g., from Feed.from_form or database operations)
            return templates.TemplateResponse(
                request=request,
                name="error.html",
                context={
                    "error": f"Error processing feed: {str(e)}",
                    "back_link": "/feed"
                },
                status_code=400
            )

    @app.post("/feed/{feed_id}/delete", response_model=None)
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
