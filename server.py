"""Entry point script for the feed-baby application."""

import os

from feed_baby import bootstrap_server
from migrate import migrate

from fastapi import FastAPI

# Configure database path from environment
db_path = os.environ.get("DATABASE_URL", "main.db")

# Configure secure cookies (HTTPS-only) from environment
# Defaults to False for local development
secure_cookies = os.environ.get("SECURE_COOKIES", "false").lower() in ("true", "1", "yes")

# Run migrations
migrate(db_path)

app = FastAPI()

# Pass db_path and secure_cookies to bootstrap
bootstrap_server(app, db_path, secure_cookies=secure_cookies)
