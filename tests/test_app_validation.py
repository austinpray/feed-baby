"""Unit tests for form validation in the app."""

from decimal import Decimal
import pytest
from pydantic import ValidationError

from feed_baby.app import FeedForm


def test_valid_feed_form():
    """Test that valid form data passes validation."""
    form = FeedForm(
        ounces=Decimal("3.5"),
        time="14:30",
        date="2025-12-09",
        timezone="America/New_York"
    )
    assert form.ounces == Decimal("3.5")
    assert form.time == "14:30"
    assert form.date == "2025-12-09"
    assert form.timezone == "America/New_York"


def test_invalid_ounces_negative():
    """Test that negative ounces are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("-1.0"),
            time="14:30",
            date="2025-12-09",
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('ounces',) for e in errors)


def test_invalid_ounces_zero():
    """Test that zero ounces are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("0"),
            time="14:30",
            date="2025-12-09",
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('ounces',) for e in errors)


def test_invalid_ounces_too_large():
    """Test that ounces over 10 are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("11.0"),
            time="14:30",
            date="2025-12-09",
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('ounces',) for e in errors)


def test_valid_ounces_boundary():
    """Test that ounces at valid boundaries are accepted."""
    # Just above 0
    form1 = FeedForm(
        ounces=Decimal("0.01"),
        time="14:30",
        date="2025-12-09",
        timezone="UTC"
    )
    assert form1.ounces == Decimal("0.01")

    # Exactly 10
    form2 = FeedForm(
        ounces=Decimal("10"),
        time="14:30",
        date="2025-12-09",
        timezone="UTC"
    )
    assert form2.ounces == Decimal("10")


def test_invalid_time_format():
    """Test that invalid time format is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="2:30",  # Should be 02:30
            date="2025-12-09",
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('time',) for e in errors)


def test_invalid_time_format_with_seconds():
    """Test that time with seconds is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="14:30:00",  # Should be 14:30
            date="2025-12-09",
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('time',) for e in errors)


def test_invalid_date_format():
    """Test that invalid date format is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="14:30",
            date="12/09/2025",  # Should be YYYY-MM-DD
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('date',) for e in errors)


def test_invalid_date_format_short():
    """Test that short date format is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="14:30",
            date="2025-1-9",  # Should be 2025-01-09
            timezone="America/New_York"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('date',) for e in errors)


def test_invalid_timezone():
    """Test that invalid timezone string is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="14:30",
            date="2025-12-09",
            timezone="Invalid/Timezone"
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('timezone',) for e in errors)


def test_empty_timezone():
    """Test that empty timezone is rejected."""
    with pytest.raises(ValidationError) as exc_info:
        FeedForm(
            ounces=Decimal("3.5"),
            time="14:30",
            date="2025-12-09",
            timezone=""
        )
    errors = exc_info.value.errors()
    assert any(e['loc'] == ('timezone',) for e in errors)


def test_valid_timezones():
    """Test that various valid timezones are accepted."""
    valid_timezones = [
        "UTC",
        "America/New_York",
        "America/Los_Angeles",
        "Europe/London",
        "Asia/Tokyo",
    ]

    for tz in valid_timezones:
        form = FeedForm(
            ounces=Decimal("3.5"),
            time="14:30",
            date="2025-12-09",
            timezone=tz
        )
        assert form.timezone == tz
