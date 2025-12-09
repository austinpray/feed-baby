"""Unit tests for Feed class."""

import sqlite3
from decimal import Decimal
import pendulum
from feed_baby.feed import Feed


def test_feed_creation_from_form():
    """Test creating Feed from form input."""
    feed = Feed.from_form(
        ounces=Decimal("3.5"),
        time="14:30",
        date="2025-12-09",
        timezone="America/New_York",
    )
    assert feed.volume_ul == 103507  # 3.5 oz in microliters
    assert feed.ounces == Decimal("3.50")


def test_feed_ounces_property():
    """Test that ounces property converts correctly."""
    feed = Feed(
        volume_ul=88721,  # 3.0 oz
        datetime=pendulum.now(),
    )
    assert feed.ounces == Decimal("3.00")


def test_feed_ounces_property_fractional():
    """Test ounces property with fractional values."""
    feed = Feed(
        volume_ul=96114,  # 3.25 oz
        datetime=pendulum.now(),
    )
    assert feed.ounces == Decimal("3.25")


def test_feed_from_db():
    """Test creating Feed from database row."""
    # Create a mock sqlite3.Row object
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE feeds (id INTEGER, volume_ul INTEGER, datetime TEXT)")
    cursor.execute("INSERT INTO feeds VALUES (1, 96114, '2025-12-09T14:30:00+00:00')")
    row = cursor.execute("SELECT * FROM feeds").fetchone()
    conn.close()

    feed = Feed.from_db(row)
    assert feed.volume_ul == 96114
    assert feed.ounces == Decimal("3.25")
    assert feed.id == 1


def test_feed_datetime_parsing():
    """Test that datetime is properly parsed from form input."""
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="09:15",
        date="2025-12-09",
        timezone="America/Los_Angeles",
    )
    assert feed.datetime.timezone.name == "America/Los_Angeles"
    assert feed.datetime.hour == 9
    assert feed.datetime.minute == 15


def test_feed_multiple_common_values():
    """Test Feed creation with multiple common feeding volumes."""
    test_cases = [
        (Decimal("1.0"), 29574),
        (Decimal("2.0"), 59147),
        (Decimal("2.5"), 73934),
        (Decimal("3.0"), 88721),
        (Decimal("3.5"), 103507),
        (Decimal("4.0"), 118294),
        (Decimal("5.0"), 147868),
    ]

    for ounces, expected_microliters in test_cases:
        feed = Feed.from_form(
            ounces=ounces, time="12:00", date="2025-12-09", timezone="UTC"
        )
        assert feed.volume_ul == expected_microliters, f"Failed for {ounces} oz"
        assert feed.ounces == ounces.quantize(Decimal("0.01"))


def test_feed_database_operations(tmp_path):
    """Test that save(), get_all(), and delete() properly handle database connections."""
    from migrate import migrate

    # Create temporary database and apply migrations
    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Test save() - create and save a feed
    feed1 = Feed.from_form(
        ounces=Decimal("3.5"), time="14:30", date="2025-12-09", timezone="UTC"
    )
    feed1.save(db_path)

    # Test get_all() - retrieve feeds
    feeds = Feed.get_all(db_path)
    assert len(feeds) == 1
    assert feeds[0].ounces == Decimal("3.50")
    assert feeds[0].datetime.hour == 14
    assert feeds[0].datetime.minute == 30

    # Save another feed
    feed2 = Feed.from_form(
        ounces=Decimal("4.0"), time="18:00", date="2025-12-09", timezone="UTC"
    )
    feed2.save(db_path)

    # Verify we now have 2 feeds
    feeds = Feed.get_all(db_path)
    assert len(feeds) == 2

    # Test delete() - remove a feed
    feed_id = feeds[0].id
    assert feed_id is not None
    deleted = Feed.delete(feed_id, db_path)
    assert deleted is True

    # Verify we now have 1 feed
    feeds = Feed.get_all(db_path)
    assert len(feeds) == 1

    # Test delete non-existent feed
    deleted = Feed.delete(9999, db_path)
    assert deleted is False


def test_feed_pagination(tmp_path):
    """Test that get_all() pagination works correctly."""
    from migrate import migrate

    # Create temporary database and apply migrations
    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Create 25 test feeds
    for i in range(25):
        feed = Feed.from_form(
            ounces=Decimal("3.0"),
            time=f"{i % 24:02d}:00",
            date="2025-12-09",
            timezone="UTC"
        )
        feed.save(db_path)

    # Test default limit (50) returns all 25
    feeds = Feed.get_all(db_path)
    assert len(feeds) == 25

    # Test custom limit
    feeds = Feed.get_all(db_path, limit=10)
    assert len(feeds) == 10

    # Test offset
    feeds_page1 = Feed.get_all(db_path, limit=10, offset=0)
    feeds_page2 = Feed.get_all(db_path, limit=10, offset=10)
    feeds_page3 = Feed.get_all(db_path, limit=10, offset=20)
    
    assert len(feeds_page1) == 10
    assert len(feeds_page2) == 10
    assert len(feeds_page3) == 5  # Only 5 remaining

    # Verify pages don't overlap
    assert feeds_page1[0].id != feeds_page2[0].id
    assert feeds_page2[0].id != feeds_page3[0].id


def test_feed_count(tmp_path):
    """Test that count() returns correct total."""
    from migrate import migrate

    # Create temporary database and apply migrations
    db_path = str(tmp_path / "test.db")
    migrate(db_path)

    # Count should be 0 initially
    assert Feed.count(db_path) == 0

    # Add feeds and verify count
    for i in range(10):
        feed = Feed.from_form(
            ounces=Decimal("3.0"),
            time="12:00",
            date="2025-12-09",
            timezone="UTC"
        )
        feed.save(db_path)

    assert Feed.count(db_path) == 10

    # Delete a feed and verify count decreases
    feeds = Feed.get_all(db_path)
    Feed.delete(feeds[0].id, db_path)
    assert Feed.count(db_path) == 9
