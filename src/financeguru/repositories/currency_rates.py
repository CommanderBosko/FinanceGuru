import json
from decimal import Decimal

from financeguru.db import get_connection
from financeguru.models.currency_rates import CurrencyRates


def get_cached(base: str) -> CurrencyRates | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM currency_rates WHERE base=?", (base,)
        ).fetchone()
    return _row_to_rates(row) if row is not None else None


def save(rates: CurrencyRates) -> None:
    rates_json = json.dumps({code: str(value) for code, value in rates.rates.items()})
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO currency_rates (base, rates_json, fetched_at) VALUES (?, ?, ?)"
            " ON CONFLICT(base) DO UPDATE SET"
            " rates_json=excluded.rates_json, fetched_at=excluded.fetched_at",
            (rates.base, rates_json, rates.fetched_at),
        )


def _row_to_rates(row) -> CurrencyRates:
    raw = json.loads(row["rates_json"])
    return CurrencyRates(
        base=row["base"],
        rates={code: Decimal(value) for code, value in raw.items()},
        fetched_at=row["fetched_at"],
    )
