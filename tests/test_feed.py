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
