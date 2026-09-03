"""Regression test for a QThread-lifecycle race in the Stock Tips tab.

Mirrors test_stocks_view.py: the toolbar's "Refresh Analyst Data" button
disables itself while a TipFetcher QThread is in flight, but the row context
menu's "Refresh Analyst Data" entry (needs_selection=False) wires straight to
the same _on_refresh handler with no such guard. Without a re-entrancy check,
triggering it again mid-fetch would deleteLater() a QThread that isRunning()
— the exact "QThread destroyed while still running" crash stop_fetcher()
elsewhere in the app exists to avoid.
"""

import time
import types
from decimal import Decimal

import yfinance

from financeguru import prices
from financeguru.models.stock_tip import StockTip
from financeguru.prices import TipFetcher, stop_fetcher
from financeguru.repositories import stock_tips as tips_repo
from financeguru.views.stock_tips_view import StockTipsView


def test_context_menu_refresh_is_noop_while_fetch_in_flight(qapp, temp_db, monkeypatch):
    tips_repo.add(StockTip(id=0, ticker="NVDA", action="Buy",
                           target_price=Decimal("180.00"), confidence=4,
                           notes=None, added_date="2026-01-01"))

    monkeypatch.setattr(prices, "_make_session", lambda: object())
    # run() builds yf.Ticker(symbol, session=...) and hands it to _fetch_one;
    # stub both so no network is touched, mirroring test_prices.py.
    monkeypatch.setattr(
        yfinance, "Ticker", lambda t, session=None: types.SimpleNamespace(ticker=t)
    )
    started: list = []

    def slow_fetch_one(ticker_obj):
        started.append(ticker_obj.ticker)
        time.sleep(0.05)
        return False, {"action": "Buy", "target": 180.0, "count": 5}

    monkeypatch.setattr(TipFetcher, "_fetch_one", staticmethod(slow_fetch_one))

    view = StockTipsView()
    try:
        view._on_refresh()  # toolbar-button path: starts the real fetch

        deadline = time.monotonic() + 5
        while not started and time.monotonic() < deadline:
            time.sleep(0.001)
        assert started, "fetcher never started"

        first_fetcher = view._fetcher
        assert first_fetcher.isRunning()
        assert not view._btn_refresh.isEnabled()

        # Simulate the row context menu's "Refresh Analyst Data" entry firing
        # while the toolbar button is disabled and a fetch is still in flight.
        view._on_refresh()

        # Must be a no-op: same fetcher instance, still running, not torn down.
        assert view._fetcher is first_fetcher
        assert view._fetcher.isRunning()
        assert view._btn_refresh.text() == "Fetching…"

        stop_fetcher(view._fetcher)
    finally:
        view.deleteLater()
        qapp.processEvents()


# --- Global month filter (added_date) ----------------------------------------
# Stock Tips previously had zero month filtering; the global month selector in
# MainWindow now drives it via select_month()/select_all(), filtering by each
# tip's own added_date. Unlike Bills/Payments/etc., Stock Tips doesn't
# contribute to the global month list (see StockTipsView — no month_keys()).


def test_defaults_to_all_and_shows_everything(qapp, temp_db):
    tips_repo.add(StockTip(id=0, ticker="NVDA", action="Buy", target_price=Decimal("180.00"),
                           confidence=4, notes=None, added_date="2026-01-01"))
    tips_repo.add(StockTip(id=0, ticker="AAPL", action="Hold", target_price=Decimal("200.00"),
                           confidence=3, notes=None, added_date="2026-06-15"))
    view = StockTipsView()
    try:
        assert view._current_key is None
        assert view._table.rowCount() == 2
    finally:
        view.deleteLater()
        qapp.processEvents()


def test_select_month_filters_by_added_date(qapp, temp_db):
    tips_repo.add(StockTip(id=0, ticker="NVDA", action="Buy", target_price=Decimal("180.00"),
                           confidence=4, notes=None, added_date="2026-01-01"))
    tips_repo.add(StockTip(id=0, ticker="AAPL", action="Hold", target_price=Decimal("200.00"),
                           confidence=3, notes=None, added_date="2026-06-15"))
    view = StockTipsView()
    try:
        view.select_month(2026, 1)
        assert view._table.rowCount() == 1
        assert view._table.item(0, 0).text() == "NVDA"

        view.select_month(2026, 6)
        assert view._table.rowCount() == 1
        assert view._table.item(0, 0).text() == "AAPL"

        view.select_all()
        assert view._table.rowCount() == 2
    finally:
        view.deleteLater()
        qapp.processEvents()


def test_select_month_with_no_matching_tips_shows_an_empty_table(qapp, temp_db):
    # Accepted per the Project Brief: a globally-selected month with no
    # relevant data for this tab is an empty state, not a bug.
    tips_repo.add(StockTip(id=0, ticker="NVDA", action="Buy", target_price=Decimal("180.00"),
                           confidence=4, notes=None, added_date="2026-01-01"))
    view = StockTipsView()
    try:
        view.select_month(2026, 12)
        assert view._table.rowCount() == 0
    finally:
        view.deleteLater()
        qapp.processEvents()
