"""Database connection helper."""

import sqlite3


def get_connection(db_path: str):
    """Get a database connection with SQLite best practices enabled.

    Enables the following SQLite features:
    - Row factory: Allows named column access (row["column_name"])
    - Foreign keys: Enforces foreign key constraints (when constraints exist)
    - Busy timeout: Waits up to 5 seconds if database is locked

    Note: WAL mode is set via migration and persists at the database level.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        A SQLite database connection with best practices configured
    """
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # Enable named column access

    # Connection-level PRAGMAs (must be set for each connection)

    # Enable foreign key constraint enforcement
    # SQLite doesn't enforce foreign keys by default for backwards compatibility.
    # This is a connection-level setting that does NOT persist, so it must be
    # set for every connection. Even though we don't have FK constraints yet,
    # enabling this prepares for future schema evolution.
    # Reference: https://www.sqlite.org/pragma.html#pragma_foreign_keys
    conn.execute("PRAGMA foreign_keys = ON")

    # Set busy timeout to 5 seconds (5000 milliseconds)
    # This prevents immediate failures when the database is locked by another
    # connection. Instead, SQLite will sleep and retry for up to 5 seconds.
    # This is a connection-level setting that must be set for each connection.
    # With WAL mode enabled, write-write conflicts are the main concern.
    # Reference: https://www.sqlite.org/c3ref/busy_timeout.html
    conn.execute("PRAGMA busy_timeout = 5000")

    return conn
