"""Database migration system."""

import sqlite3
from pathlib import Path


def migrate(db_path: str) -> None:
    """Run database migrations.
    
    Args:
        db_path: Path to SQLite database file
    """
    conn = sqlite3.connect(db_path)
    
    current_version = conn.execute("PRAGMA user_version").fetchone()[0]
    
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    with conn:
        for migration_file in migration_files:
            version = int(migration_file.stem[:4])
            if version > current_version:
                sql = migration_file.read_text()
                conn.executescript(sql)
    
    conn.close()
