"""Database connection utilities."""
import sqlite3


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.Connection(db_path)
    conn.row_factory = sqlite3.Row
    return conn
