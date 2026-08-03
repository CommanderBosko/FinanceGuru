"""Regression test for a QThread-lifecycle race in the Stocks tab.

The toolbar's "Refresh Prices" button disables itself while a PriceFetcher
QThread is in flight, but the row context menu's "Refresh Prices" entry
(registered with needs_selection=False in attach_row_menu) wires straight to
the same _on_refresh handler with no such guard. Without a re-entrancy check,
triggering it again mid-fetch would deleteLater() a QThread that isRunning()
— the exact "QThread destroyed while still running" crash stop_fetcher()
elsewhere in the app exists to avoid.

This drives a real PriceFetcher (network call stubbed out, like test_prices.py
does) so isRunning() reflects genuine thread state rather than a mock.
"""

import time
from decimal import Decimal

from financeguru import prices
from financeguru.models.stock import Stock
from financeguru.prices import PriceFetcher, stop_fetcher
from financeguru.repositories import stocks as stock_repo
from financeguru.views.stocks_view import StocksView


def test_context_menu_refresh_is_noop_while_fetch_in_flight(qapp, temp_db, monkeypatch):
    stock_repo.add(Stock(ticker="AAPL", shares=Decimal("10"),
                         purchase_price=Decimal("100"), purchase_date="2025-01-01"))

    monkeypatch.setattr(prices, "_make_session", lambda: object())
    started: list = []

    def slow_fetch(yf, ticker, session):
        started.append(ticker)
        time.sleep(0.05)
        return 1.0

    monkeypatch.setattr(PriceFetcher, "_fetch_price", staticmethod(slow_fetch))

    view = StocksView()
    try:
        view._on_refresh()  # toolbar-button path: starts the real fetch

        deadline = time.monotonic() + 5
        while not started and time.monotonic() < deadline:
            time.sleep(0.001)
        assert started, "fetcher never started"

        first_fetcher = view._fetcher
        assert first_fetcher.isRunning()
        assert not view._btn_refresh.isEnabled()

        # Simulate the row context menu's "Refresh Prices" entry firing while
        # the toolbar button is disabled and a fetch is still in flight.
        view._on_refresh()

        # Must be a no-op: same fetcher instance, still running, not torn down.
        assert view._fetcher is first_fetcher
        assert view._fetcher.isRunning()
        assert view._btn_refresh.text() == "Fetching…"

        stop_fetcher(view._fetcher)
    finally:
        view.deleteLater()
        qapp.processEvents()
