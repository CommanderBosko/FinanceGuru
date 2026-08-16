"""Round-trip tests for the currency_rates cache table.

save()/get_cached() must round-trip Decimal rates exactly (through the
rates_json string, not the REAL/Decimal adapter used elsewhere) and upsert
per base currency rather than accumulating history.
"""

from decimal import Decimal

from financeguru.models.currency_rates import CurrencyRates
from financeguru.repositories import currency_rates as rates_repo


def test_get_cached_returns_none_when_empty(temp_db):
    assert rates_repo.get_cached("USD") is None


def test_save_and_get_cached_round_trips_decimal_rates(temp_db):
    rates_repo.save(
        CurrencyRates("USD", {"EUR": Decimal("0.9234"), "GBP": Decimal("0.789")}, "2026-08-15")
    )
    cached = rates_repo.get_cached("USD")
    assert cached.base == "USD"
    assert cached.rates == {"EUR": Decimal("0.9234"), "GBP": Decimal("0.789")}
    assert cached.fetched_at == "2026-08-15"


def test_save_upserts_rather_than_duplicating(temp_db):
    rates_repo.save(CurrencyRates("USD", {"EUR": Decimal("0.90")}, "2026-08-14"))
    rates_repo.save(CurrencyRates("USD", {"EUR": Decimal("0.92")}, "2026-08-15"))
    cached = rates_repo.get_cached("USD")
    assert cached.rates == {"EUR": Decimal("0.92")}
    assert cached.fetched_at == "2026-08-15"


def test_different_bases_are_cached_independently(temp_db):
    rates_repo.save(CurrencyRates("USD", {"EUR": Decimal("0.92")}, "2026-08-15"))
    rates_repo.save(CurrencyRates("EUR", {"USD": Decimal("1.08")}, "2026-08-15"))
    assert rates_repo.get_cached("USD").rates == {"EUR": Decimal("0.92")}
    assert rates_repo.get_cached("EUR").rates == {"USD": Decimal("1.08")}
