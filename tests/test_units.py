"""Unit tests for volume conversion utilities."""

from decimal import Decimal
from feed_baby.units import ounces_to_microliters, microliters_to_ounces


def test_ounces_to_microliters_whole_number():
    """Test conversion of whole number ounces."""
    assert ounces_to_microliters(Decimal("3.0")) == 88721


def test_ounces_to_microliters_fractional():
    """Test conversion of fractional ounces."""
    assert ounces_to_microliters(Decimal("3.25")) == 96114
    assert ounces_to_microliters(Decimal("3.5")) == 103507


def test_ounces_to_microliters_rounding():
    """Test proper rounding behavior."""
    # 2.75 oz = 81327.125 µL -> should round to 81327
    assert ounces_to_microliters(Decimal("2.75")) == 81327


def test_microliters_to_ounces_whole():
    """Test conversion back to ounces."""
    assert microliters_to_ounces(88721) == Decimal("3.00")


def test_microliters_to_ounces_fractional():
    """Test fractional ounces display."""
    assert microliters_to_ounces(96114) == Decimal("3.25")


def test_round_trip_conversion():
    """Test that round-trip conversion maintains precision."""
    original = Decimal("3.25")
    microliters = ounces_to_microliters(original)
    back_to_ounces = microliters_to_ounces(microliters)
    assert back_to_ounces == original


def test_round_trip_conversion_multiple_values():
    """Test round-trip conversion for multiple common values."""
    test_values = [
        Decimal("1.0"),
        Decimal("1.5"),
        Decimal("2.0"),
        Decimal("2.5"),
        Decimal("3.0"),
        Decimal("3.5"),
        Decimal("4.0"),
        Decimal("4.5"),
        Decimal("5.0"),
    ]

    for original in test_values:
        microliters = ounces_to_microliters(original)
        back_to_ounces = microliters_to_ounces(microliters)
        assert back_to_ounces == original, f"Round-trip failed for {original} oz"


def test_edge_case_min_value():
    """Test minimum expected value (1.0 oz)."""
    assert ounces_to_microliters(Decimal("1.0")) == 29574


def test_edge_case_max_value():
    """Test maximum expected value (5.0 oz)."""
    assert ounces_to_microliters(Decimal("5.0")) == 147868


def test_precision_two_decimal_places():
    """Test that ounces display shows exactly 2 decimal places."""
    result = microliters_to_ounces(88721)
    # Check that it has exactly 2 decimal places
    assert result == Decimal("3.00")
    assert str(result) == "3.00"
