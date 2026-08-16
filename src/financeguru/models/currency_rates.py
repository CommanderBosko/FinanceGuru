from dataclasses import dataclass
from decimal import Decimal


@dataclass
class CurrencyRates:
    """A cached exchange-rate snapshot, relative to one pivot currency.

    ``rates`` maps a 3-letter currency code to its value relative to 1 unit of
    ``base`` (``base`` itself included with rate ``Decimal("1")``), so the
    conversion between any two listed currencies is a single cross-rate
    division — ``amount * rates[to] / rates[from]`` — rather than a fetch per
    currency pair. ``fetched_at`` is the rate table's effective date
    (``YYYY-MM-DD``, as reported by the API), not necessarily today — it's
    what a cache-hit or offline fallback shows the user as "Rates as of …".

    Unlike the row-backed models (``Bill``, ``Expense``, …) this isn't a table
    of editable records with an id — it's a singleton cache keyed by ``base``,
    so there's no ``id`` field to round-trip.
    """

    base: str
    rates: dict[str, Decimal]
    fetched_at: str
