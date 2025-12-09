"""Database connection helper."""

import sqlite3


def get_connection(db_path: str):
    """Get a database connection.

    Args:
        db_path: Path to the SQLite database file

    Returns:
        A SQLite database connection with Row factory enabled
    """
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row  # Enable named column access
    return conn
