"""Unit conversion utilities for volume measurements."""

from decimal import Decimal, ROUND_HALF_UP

# Conversion constant: 1 fluid ounce (US) = 29.5735 milliliters = 29,573.5 microliters
OZ_TO_MICROLITERS = Decimal("29573.5")
MICROLITERS_TO_OZ = Decimal("1") / OZ_TO_MICROLITERS


def ounces_to_microliters(ounces: Decimal) -> int:
    """Convert fluid ounces to microliters as integer.

    Args:
        ounces: Volume in fluid ounces (US)

    Returns:
        Volume in microliters, rounded to nearest integer

    Examples:
        >>> ounces_to_microliters(Decimal("3.0"))
        88721
        >>> ounces_to_microliters(Decimal("3.25"))
        96114
    """
    microliters = ounces * OZ_TO_MICROLITERS
    # Round to nearest integer using ROUND_HALF_UP (standard rounding)
    return int(microliters.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def microliters_to_ounces(microliters: int) -> Decimal:
    """Convert microliters to fluid ounces as Decimal.

    Args:
        microliters: Volume in microliters

    Returns:
        Volume in fluid ounces (US), rounded to 2 decimal places

    Examples:
        >>> microliters_to_ounces(88721)
        Decimal('3.00')
        >>> microliters_to_ounces(96114)
        Decimal('3.25')
    """
    ounces = Decimal(microliters) * MICROLITERS_TO_OZ
    # Round to 2 decimal places for display
    return ounces.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
