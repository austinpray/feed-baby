"""Entry point script for the feed-baby application."""

import os

from feed_baby import bootstrap_server
from migrate import migrate

from fastapi import FastAPI

# Configure database path from environment
db_path = os.environ.get("DATABASE_URL", "main.db")

# Run migrations
migrate(db_path)

app = FastAPI()

# Pass db_path to bootstrap
bootstrap_server(app, db_path)
