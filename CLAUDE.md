# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

feed-baby is a FastAPI-based web application for tracking baby feeding data. Users can log feeds with volume (in ounces) and timestamp, view feeding history, and export the future feeding schedule to an ical feed.

## Development Commands

### Running the Application

```bash
# Development mode with auto-reload
fastapi dev server.py
```

### Testing

```bash
# Run all tests with verbose output
pytest -v

# Run specific test file
pytest -v tests/test_feed.py

# Run specific test
pytest -v tests/test_feed.py::test_name
```

### Code Quality

```bash
# Run linter
uv run ruff check

# Run type checker
uv run ty
```

### Database Management

```bash
# Run migrations manually
uv run migrate.py

# Migrations run automatically on server startup
# Database location: main.db (default) or set via DATABASE_URL env var
```

## Architecture

### Application Structure

- **server.py**: Entry point that runs migrations and bootstraps the FastAPI app
- **feed_baby/app.py**: Contains `bootstrap_server()` which registers all routes
- **feed_baby/feed.py**: Core `Feed` model with CRUD operations and conversions
- **feed_baby/db.py**: Database connection helper (SQLite with Row factory)
- **feed_baby/units.py**: Volume conversion utilities between ounces and microliters
- **migrate.py**: Simple migration system that auto-discovers SQL files in migrations/
- **templates/**: Jinja2 HTML templates for the web UI

### Database Layer

The app uses raw SQLite with a simple migration system:

- **Migration files**: Numbered SQL files in `migrations/` directory (e.g., `0001_init.sql`)
- **Version tracking**: Uses SQLite's `PRAGMA user_version` to track applied migrations
- **Auto-discovery**: `migrate.py` automatically finds and applies migrations in order
- **Connection pattern**: Each operation opens a connection, executes, closes (no connection pooling)
- **Row access**: Uses `sqlite3.Row` factory for named column access

### Feed Model Pattern

The `Feed` class follows a specific design pattern:

- **Internal storage**: Volume stored as integer microliters for precision
- **User interface**: Volume exposed as `Decimal` ounces via property
- **Datetime handling**: Uses pendulum library, stores as ISO8601 UTC strings in database
- **Factory methods**:
  - `from_form()`: Create from user form input (ounces, separate date/time/timezone)
  - `from_db()`: Create from database row with named column access
- **CRUD methods**: All methods require `db_path` parameter (passed from `app.state.db_path`)

### Route Registration

Routes are defined inside `bootstrap_server()` in `feed_baby/app.py`. The FastAPI app instance and `db_path` are passed in, with `db_path` stored in `app.state` for route access. Key routes:

- `GET /`: Display all feeds (newest first)
- `GET /feed`: Show feed input form
- `POST /feed`: Create new feed from form data
- `POST /feed/{feed_id}/delete`: Delete specific feed (returns 303 redirect)

### Configuration

Configuration is not currently implemented but is planned via TOML files (see `config.sample.toml`):
- `daily_goal_ounces`: Target daily feeding volume
- `max_interval_hours`: Maximum time between feeds
- `sleep_hours`: Expected sleep duration

## Testing Patterns

Tests use pytest with temporary database files for isolation. When writing tests:

- Create a temporary database path for each test (use `tmp_path` fixture)
- Test both the microliters (internal) and ounces (display) representations
- For `Feed.from_form()`, test timezone handling (input timezone → stored as UTC)
- For database operations, verify both success and failure cases (e.g., delete non-existent record)
