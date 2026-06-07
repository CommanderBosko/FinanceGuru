"""Exact monetary arithmetic helpers.

Money is represented as :class:`decimal.Decimal` throughout the domain and
computation layers so that values never accumulate binary floating-point error
(notably in the month-by-month debt simulation). Values are stored in SQLite as
REAL and coerced back to Decimal at the repository boundary via :func:`to_decimal`;
because every stored amount is cent-quantized, the double round-trip is exact.
"""

from decimal import Decimal, ROUND_HALF_UP

ZERO = Decimal("0")
CENT = Decimal("0.01")


def to_decimal(value, default: str = "0") -> Decimal:
    """Coerce a DB/UI value (float, int, str, Decimal, None) to an exact Decimal.

    Floats are routed through ``str`` so that e.g. 19.99 becomes Decimal('19.99')
    rather than the binary-approximation tail of float 19.99.
    """
    if value is None:
        return Decimal(default)
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def optional_decimal(value) -> Decimal | None:
    """Like :func:`to_decimal` but preserves SQL NULL / missing values as None."""
    return None if value is None else to_decimal(value)


def cents(value) -> Decimal:
    """Decimal quantized to whole cents, rounding half away from zero."""
    return to_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)
