"""Simple SQLite migration system with automatic discovery."""

import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def migrate(db_path: str):
    """Apply pending database migrations.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]

    # Discover and sort migration files
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    for migration_file in migration_files:
        # Extract version number from filename (first 4 digits)
        version = int(migration_file.stem[:4])

        # Only apply migrations newer than current version
        if version > current_version:
            sql = migration_file.read_text()
            conn.executescript(sql)

    conn.close()


if __name__ == "__main__":
    import os

    db_path = os.environ.get("DATABASE_URL", "main.db")
    migrate(db_path)
