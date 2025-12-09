"""Feed model for tracking baby feedings."""
from decimal import Decimal
from typing import Self
import pendulum
from feed_baby.database import get_connection


class Feed:
    """Represents a baby feeding record."""
    
    def __init__(
        self,
        ounces: Decimal,
        datetime: pendulum.DateTime,
        id: int | None = None,
    ):
        self.id = id
        self.ounces = ounces
        self.datetime = datetime
        # Store volume in microliters internally
        self.volume_ul = int(ounces * Decimal("29573.5"))
    
    @classmethod
    def from_form(
        cls,
        ounces: Decimal,
        time: str,
        date: str,
        timezone: str,
    ) -> Self:
        """Create a Feed from form data."""
        dt_str = f"{date} {time}"
        tz = pendulum.timezone(timezone)
        dt = pendulum.parse(dt_str, tz=tz)
        return cls(ounces=ounces, datetime=dt)
    
    @classmethod
    def from_db(cls, row) -> Self:
        """Create a Feed from a database row."""
        volume_ul = row[1]
        ounces = Decimal(volume_ul) / Decimal("29573.5")
        dt = pendulum.parse(row[2])
        return cls(
            id=row[0],
            ounces=ounces,
            datetime=dt,
        )
    
    def save(self, db_path: str) -> None:
        """Save the feed to the database. HAS CONNECTION LEAK!"""
        conn = get_connection(db_path)
        conn.execute(
            "INSERT INTO feeds (volume_ul, datetime) VALUES (?, ?)",
            (self.volume_ul, self.datetime.to_iso8601_string()),
        )
        conn.commit()
        conn.close()  # Won't execute if commit() raises
    
    @property
    def display_time(self) -> str:
        """Get human-readable time string."""
        return self.datetime.format("h:mm A")
    
    @property
    def display_date(self) -> str:
        """Get human-readable date string."""
        return self.datetime.format("MMM D, YYYY")
    
    @property
    def milliliters(self) -> Decimal:
        """Get volume in milliliters."""
        return Decimal(self.volume_ul) / Decimal("1000")
    
    @classmethod
    def get_feed(cls, feed_id: int, db_path: str) -> Self | None:
        """Get a specific feed by ID."""
        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT id, volume_ul, datetime FROM feeds WHERE id = ?",
            (feed_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row is None:
            return None
        return cls.from_db(row)
    
    @classmethod
    def get_all(cls, db_path: str) -> list[Self]:
        """Get all feeds, ordered by datetime descending. HAS CONNECTION LEAK!"""
        conn = get_connection(db_path)
        cursor = conn.execute(
            "SELECT id, volume_ul, datetime FROM feeds ORDER BY datetime DESC"
        )
        feeds = [cls.from_db(row) for row in cursor.fetchall()]
        conn.close()  # Won't execute if fetchall() raises
        return feeds
    
    @classmethod
    def count(cls, db_path: str) -> int:
        """Get total count of feeds."""
        conn = get_connection(db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM feeds")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    @classmethod
    def delete(cls, feed_id: int, db_path: str) -> bool:
        """Delete a feed by ID. Returns True if deleted. HAS CONNECTION LEAK!"""
        conn = get_connection(db_path)
        cursor = conn.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
        conn.commit()
        conn.close()  # Won't execute if commit() raises
        return cursor.rowcount > 0
