"""Behavioral tests for the Currency Converter tab.

The construction/refresh contract is covered by test_views_smoke (which also
patches RatesFetcher.start to a no-op); these tests drive conversion math,
swap, and preference persistence directly, and feed _on_rates_ready /
_on_fetch_error to simulate fetch outcomes without touching the network --
RatesFetcher's own request/parsing logic is covered in test_rates.py.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.currencies import PIVOT_BASE
from financeguru.rates import RatesFetcher
from financeguru.repositories import currency_rates as rates_repo
from financeguru.repositories import preferences as prefs_repo
from financeguru.views.currency_converter_view import CurrencyConverterView

_RATES = {"USD": Decimal("1"), "EUR": Decimal("0.5"), "GBP": Decimal("0.4")}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(RatesFetcher, "start", lambda self: None)


@pytest.fixture
def view(qapp, temp_db):
    v = CurrencyConverterView()
    yield v
    v.deleteLater()
    qapp.processEvents()


def test_defaults_to_usd_eur_with_no_result_before_rates_load(view):
    assert view._from_combo.currentData() == "USD"
    assert view._to_combo.currentData() == "EUR"
    assert view._result.text() == "—"


def test_recomputes_once_rates_arrive(view):
    view._on_rates_ready(_RATES, "2026-08-15")
    assert view._result.text() == "50.00 EUR"
    assert "Rates as of 2026-08-15" in view._status.text()


def test_rates_are_cached_for_next_launch(view):
    view._on_rates_ready(_RATES, "2026-08-15")
    cached = rates_repo.get_cached(PIVOT_BASE)
    assert cached is not None
    assert cached.rates["EUR"] == Decimal("0.5")
    assert cached.fetched_at == "2026-08-15"


def test_fetch_error_with_no_cache_shows_message_and_blanks_result(view):
    view._on_fetch_error("Could not fetch exchange rates. Check your connection and try again.")
    assert view._result.text() == "—"
    assert "connection" in view._status.text()


def test_fetch_error_with_existing_cache_keeps_showing_it(view):
    view._on_rates_ready(_RATES, "2026-08-15")
    view._on_fetch_error("network down")
    assert "Offline" in view._status.text()
    assert view._result.text() == "50.00 EUR"  # unchanged -- still usable offline


def test_swap_exchanges_from_and_to(view):
    view._on_rates_ready(_RATES, "2026-08-15")
    view._to_combo.setCurrentIndex(view._to_combo.findData("GBP"))
    view._on_swap()
    assert view._from_combo.currentData() == "GBP"
    assert view._to_combo.currentData() == "USD"


def test_input_changes_persist_as_preferences(view):
    view._to_combo.setCurrentIndex(view._to_combo.findData("GBP"))
    view._amount.setValue(250.0)
    assert prefs_repo.get("currency_converter.to") == "GBP"
    assert prefs_repo.get("currency_converter.amount") == "250.00"


def test_reopening_the_view_restores_saved_preferences(view, qapp):
    view._to_combo.setCurrentIndex(view._to_combo.findData("GBP"))
    view._amount.setValue(250.0)

    reopened = CurrencyConverterView()
    assert reopened._to_combo.currentData() == "GBP"
    assert reopened._amount.value() == 250.0
    reopened.deleteLater()
    qapp.processEvents()


def test_refresh_never_triggers_a_network_fetch(view, monkeypatch):
    # refresh() is DB-local only (matching Stocks/Stock Tips' convention) --
    # even with a stale/missing cache, it must not itself start a fetch.
    started = []
    monkeypatch.setattr(RatesFetcher, "start", lambda self: started.append(True))
    view.refresh()
    assert started == []


def test_refresh_reloads_preferences(view):
    # Simulates a DB restore swapping in different saved preferences: refresh()
    # must pick them up rather than leave the combos/amount on pre-restore
    # values (the "view goes stale after a DB restore" bug class).
    prefs_repo.set("currency_converter.from", "GBP")
    prefs_repo.set("currency_converter.to", "JPY")
    prefs_repo.set("currency_converter.amount", "42.00")

    view.refresh()

    assert view._from_combo.currentData() == "GBP"
    assert view._to_combo.currentData() == "JPY"
    assert view._amount.value() == 42.00


def test_refresh_button_forces_a_fetch_even_when_cache_is_fresh(view, monkeypatch):
    view._on_rates_ready(_RATES, date.today().isoformat())
    started = []
    monkeypatch.setattr(RatesFetcher, "start", lambda self: started.append(True))
    view._refresh_btn.click()
    assert started == [True]


def test_zero_decimal_currency_shows_no_decimal_places(view):
    # JPY has no minor unit; money.cents()'s 2-decimal convention is wrong for
    # it (see currencies.ZERO_DECIMAL_CURRENCIES).
    rates = dict(_RATES, JPY=Decimal("150"))
    view._on_rates_ready(rates, "2026-08-15")
    view._to_combo.setCurrentIndex(view._to_combo.findData("JPY"))
    assert view._result.text() == "15,000 JPY"
    assert "." not in view._result.text()


def test_stale_saved_currency_falls_back_to_documented_default(view, qapp):
    # A saved code that no longer matches any CURRENCIES entry (list edited,
    # or a corrupted row) must fall back to DEFAULT_FROM/DEFAULT_TO, not
    # whatever sits at combo index 0.
    prefs_repo.set("currency_converter.from", "XXX")

    reopened = CurrencyConverterView()
    assert reopened._from_combo.currentData() == "USD"  # DEFAULT_FROM, not index 0
    reopened.deleteLater()
    qapp.processEvents()


def test_swap_persists_and_recomputes_exactly_once(view, monkeypatch):
    view._on_rates_ready(_RATES, "2026-08-15")
    view._to_combo.setCurrentIndex(view._to_combo.findData("GBP"))

    calls = []
    monkeypatch.setattr(prefs_repo, "set_many", lambda items: calls.append(items))
    view._on_swap()

    assert len(calls) == 1


def test_rates_ready_updates_ui_even_if_the_cache_write_fails(view, monkeypatch):
    def boom(rates):
        raise OSError("disk full")

    monkeypatch.setattr(rates_repo, "save", boom)
    view._on_rates_ready(_RATES, "2026-08-15")

    assert view._result.text() == "50.00 EUR"
    assert "Rates as of 2026-08-15" in view._status.text()
