import sqlite3
from decimal import Decimal
from typing import Self
import pendulum

from feed_baby.units import ounces_to_microliters, microliters_to_ounces


class Feed:
    """Represents a baby feeding record.

    Internally stores volume as integer microliters for precision.
    Provides ounces as a property for display/user interaction.
    """

    id: int | None  # Database ID (None if not yet saved)
    volume_ul: int  # Volume in microliters
    datetime: pendulum.DateTime

    def __init__(self, volume_ul: int, datetime: pendulum.DateTime, id: int | None = None):
        """Initialize Feed with microliters and datetime.

        Args:
            volume_ul: Volume in microliters
            datetime: When the feeding occurred
            id: Database ID (optional, None if not yet saved)
        """
        self.id = id
        self.volume_ul = volume_ul
        self.datetime = datetime

    @property
    def ounces(self) -> Decimal:
        """Get volume in ounces for display.

        Returns:
            Volume in fluid ounces, rounded to 2 decimal places
        """
        return microliters_to_ounces(self.volume_ul)

    def save(self, db_path: str):
        """Save feed to database.

        Args:
            db_path: Path to SQLite database
        """
        from feed_baby.db import get_connection

        conn = get_connection(db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT INTO feeds (volume_ul, datetime) VALUES (?, ?)",
                    (self.volume_ul, self.datetime.in_timezone("UTC").to_iso8601_string()),
                )
        finally:
            conn.close()

    @classmethod
    def from_form(cls, ounces: Decimal, time: str, date: str, timezone: str) -> Self:
        """Create Feed from form input (ounces-based).

        Args:
            ounces: Volume in fluid ounces from user input
            time: Time string in HH:mm format
            date: Date string in YYYY-MM-DD format
            timezone: IANA timezone identifier

        Returns:
            Feed instance with volume converted to microliters
        """
        datetime = pendulum.from_format(
            f"{date}T{time}", "YYYY-MM-DDTHH:mm", tz=timezone
        )
        volume_ul = ounces_to_microliters(ounces)
        return cls(volume_ul, datetime)

    @classmethod
    def from_db(cls, row: sqlite3.Row) -> Self:
        """Create Feed from database row.

        Args:
            row: Database row with named column access

        Returns:
            Feed instance
        """
        datetime_parsed = pendulum.parse(row['datetime'])
        if not isinstance(datetime_parsed, pendulum.DateTime):
            raise ValueError(f"Expected DateTime, got {type(datetime_parsed)}")
        return cls(
            volume_ul=row['volume_ul'],
            datetime=datetime_parsed,
            id=row['id']
        )

    @classmethod
    def get_all(cls, db_path: str) -> list[Self]:
        """Get all feeds from database, ordered newest to oldest.

        Args:
            db_path: Path to SQLite database

        Returns:
            List of Feed instances ordered by datetime DESC
        """
        from feed_baby.db import get_connection

        conn = get_connection(db_path)
        try:
            cursor = conn.execute(
                "SELECT id, volume_ul, datetime FROM feeds ORDER BY datetime DESC"
            )
            feeds = [cls.from_db(row) for row in cursor.fetchall()]
            return feeds
        finally:
            conn.close()

    @classmethod
    def delete(cls, feed_id: int, db_path: str) -> bool:
        """Delete a feed from the database.

        Args:
            feed_id: The ID of the feed to delete
            db_path: Path to SQLite database

        Returns:
            True if feed was deleted, False if feed not found
        """
        from feed_baby.db import get_connection

        conn = get_connection(db_path)
        try:
            with conn:
                cursor = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
                deleted = cursor.rowcount > 0
                return deleted
        finally:
            conn.close()
