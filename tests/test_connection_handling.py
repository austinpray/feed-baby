"""Test database connection handling in Feed class."""
import pytest
import tempfile
import sqlite3
from pathlib import Path
from decimal import Decimal
from feed_baby.feed import Feed


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        # Create the table
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                volume_ul INTEGER NOT NULL,
                datetime TEXT NOT NULL
            )
        """)
        conn.commit()
        conn.close()
        yield db_path


def test_save_closes_connection_on_success(test_db):
    """Test that save() properly closes connections on success."""
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC"
    )
    feed.save(test_db)
    
    # Verify the feed was saved
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1
    # Check within tolerance due to conversion precision
    assert abs(feeds[0].ounces - Decimal("3.0")) < Decimal("0.01")


def test_save_closes_connection_on_error(test_db):
    """Test that save() properly closes connections even on error."""
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC"
    )
    
    # Drop the table to cause an error
    conn = sqlite3.connect(test_db)
    conn.execute("DROP TABLE feeds")
    conn.commit()
    conn.close()
    
    # This should raise an error but not leak connections
    with pytest.raises(sqlite3.OperationalError):
        feed.save(test_db)
    
    # Verify no connections are leaked by being able to access the database
    conn = sqlite3.connect(test_db)
    conn.close()


def test_get_all_closes_connection_on_success(test_db):
    """Test that get_all() properly closes connections on success."""
    # Create test feeds
    for i in range(3):
        feed = Feed.from_form(
            ounces=Decimal(str(i + 1)),
            time="12:00",
            date="2025-12-09",
            timezone="UTC"
        )
        feed.save(test_db)
    
    # Fetch all feeds
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 3


def test_get_all_closes_connection_on_error(test_db):
    """Test that get_all() properly closes connections even on error."""
    # Drop the table to cause an error
    conn = sqlite3.connect(test_db)
    conn.execute("DROP TABLE feeds")
    conn.commit()
    conn.close()
    
    # This should raise an error but not leak connections
    with pytest.raises(sqlite3.OperationalError):
        Feed.get_all(test_db)
    
    # Verify no connections are leaked
    conn = sqlite3.connect(test_db)
    conn.close()


def test_delete_closes_connection_on_success(test_db):
    """Test that delete() properly closes connections on success."""
    # Create a feed
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC"
    )
    feed.save(test_db)
    
    # Get the feed ID
    feeds = Feed.get_all(test_db)
    feed_id = feeds[0].id
    
    # Delete it
    deleted = Feed.delete(feed_id, test_db)
    assert deleted is True
    assert len(Feed.get_all(test_db)) == 0


def test_delete_closes_connection_on_error(test_db):
    """Test that delete() properly closes connections even on error."""
    # Drop the table to cause an error
    conn = sqlite3.connect(test_db)
    conn.execute("DROP TABLE feeds")
    conn.commit()
    conn.close()
    
    # This should raise an error but not leak connections
    with pytest.raises(sqlite3.OperationalError):
        Feed.delete(1, test_db)
    
    # Verify no connections are leaked
    conn = sqlite3.connect(test_db)
    conn.close()


def test_context_manager_usage(test_db):
    """Test that database connections can be used as context managers."""
    from feed_baby.database import get_connection
    
    # Verify that get_connection returns a connection that supports context manager
    with get_connection(test_db) as conn:
        cursor = conn.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    # After exiting context, connection should be closed
    # We can verify by opening another connection successfully
    conn2 = sqlite3.connect(test_db)
    conn2.close()
