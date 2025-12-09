"""Tests for the Feed model."""

import pytest
import tempfile
from pathlib import Path
from decimal import Decimal

import pendulum

from feed_baby.feed import Feed
from migrate import migrate


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = str(Path(tmpdir) / "test.db")
        migrate(db_path)
        yield db_path


def test_feed_from_form():
    """Test creating a Feed from form data."""
    feed = Feed.from_form(
        ounces=Decimal("3.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    
    assert feed.ounces == Decimal("3.00")
    assert feed.datetime.year == 2025
    assert feed.datetime.month == 12
    assert feed.datetime.day == 9
    assert feed.datetime.hour == 12
    assert feed.datetime.minute == 0


def test_feed_ounces_conversion():
    """Test ounces to microliters conversion."""
    # 1 oz ≈ 29.5735 ml ≈ 29573.5 µl
    feed = Feed.from_form(
        ounces=Decimal("1.0"),
        time="12:00",
        date="2025-12-09",
        timezone="UTC",
    )
    
    # Check volume is approximately correct
    ml = feed.volume_ul / 1000
    assert abs(ml - 29.5735) < 0.1


def test_feed_save_and_retrieve(test_db):
    """Test saving and retrieving a feed."""
    feed = Feed.from_form(
        ounces=Decimal("3.5"),
        time="14:30",
        date="2025-12-09",
        timezone="America/New_York",
    )
    
    feed.save(test_db)
    
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1
    assert feeds[0].ounces == Decimal("3.50")


def test_feed_delete(test_db):
    """Test deleting a feed."""
    feed = Feed.from_form(
        ounces=Decimal("2.0"),
        time="10:00",
        date="2025-12-09",
        timezone="UTC",
    )
    feed.save(test_db)
    
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 1
    
    feed_id = feeds[0].id
    deleted = Feed.delete(feed_id, test_db)
    assert deleted is True
    
    feeds = Feed.get_all(test_db)
    assert len(feeds) == 0


def test_feed_delete_nonexistent(test_db):
    """Test deleting a non-existent feed."""
    deleted = Feed.delete(999, test_db)
    assert deleted is False
