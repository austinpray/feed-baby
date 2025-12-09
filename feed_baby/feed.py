"""Feed model for tracking baby feedings."""

import sqlite3
from decimal import Decimal
from typing import Self

import pendulum


def get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection."""
    conn = sqlite3.Connection(db_path)
    conn.row_factory = sqlite3.Row
    return conn


class Feed:
    """Represents a single feeding event."""

    def __init__(
        self,
        volume_ul: int,
        datetime: pendulum.DateTime,
        id: int | None = None,
    ):
        """Initialize a Feed instance.
        
        Args:
            volume_ul: Volume in microliters
            datetime: Pendulum datetime object
            id: Optional database ID
        """
        self.id = id
        self.volume_ul = volume_ul
        self.datetime = datetime

    @property
    def ounces(self) -> Decimal:
        """Convert volume to ounces."""
        ml = Decimal(self.volume_ul) / Decimal(1000)
        oz_per_ml = Decimal("0.033814")
        return (ml * oz_per_ml).quantize(Decimal("0.01"))

    @classmethod
    def from_form(
        cls, ounces: Decimal, time: str, date: str, timezone: str
    ) -> Self:
        """Create a Feed from form data.
        
        Args:
            ounces: Volume in ounces
            time: Time string in HH:MM format
            date: Date string in YYYY-MM-DD format
            timezone: Timezone name
            
        Returns:
            Feed instance
        """
        ml_per_oz = Decimal("29.5735")
        ml = ounces * ml_per_oz
        volume_ul = int(ml * 1000)

        dt = pendulum.parse(f"{date} {time}", tz=timezone)
        return cls(volume_ul=volume_ul, datetime=dt)

    @classmethod
    def from_db(cls, row: sqlite3.Row) -> Self:
        """Create a Feed from a database row.
        
        Args:
            row: SQLite row object
            
        Returns:
            Feed instance
        """
        return cls(
            id=row["id"],
            volume_ul=row["volume_ul"],
            datetime=pendulum.parse(row["datetime"]),
        )

    def save(self, db_path: str) -> None:
        """Save the feed to the database.
        
        Args:
            db_path: Path to SQLite database file
        """
        with get_connection(db_path) as conn:
            conn.execute(
                "INSERT INTO feeds (volume_ul, datetime) VALUES (?, ?)",
                (self.volume_ul, self.datetime.to_iso8601_string()),
            )
            conn.commit()

    @classmethod
    def get_all(cls, db_path: str) -> list[Self]:
        """Get all feeds from the database.
        
        Args:
            db_path: Path to SQLite database file
            
        Returns:
            List of Feed instances
        """
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                "SELECT id, volume_ul, datetime FROM feeds ORDER BY datetime DESC"
            )
            feeds = [cls.from_db(row) for row in cursor.fetchall()]
        return feeds

    @classmethod
    def delete(cls, feed_id: int, db_path: str) -> bool:
        """Delete a feed by ID.
        
        Args:
            feed_id: ID of the feed to delete
            db_path: Path to SQLite database file
            
        Returns:
            True if deleted, False if not found
        """
        with get_connection(db_path) as conn:
            cursor = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
            conn.commit()
            return cursor.rowcount > 0
