"""Tests for the fetch plumbing in rates.py.

Mirrors test_prices.py's shape: the RatesFetcher QThread is exercised with the
network stubbed out (urllib.request.urlopen replaced), so these are fast and
deterministic. View-level consumption of rates_ready/fetch_error is covered in
test_currency_converter_view.py; the cache round-trip in
test_currency_rates_repo.py.
"""

import json
import urllib.request
from decimal import Decimal

from PySide6.QtCore import QEventLoop, QTimer

from financeguru.rates import RatesFetcher, stop_fetcher


def _run_to_finish(fetcher, timeout_ms=5000):
    """Start the fetcher and pump the event loop until it emits ``finished``."""
    loop = QEventLoop()
    fetcher.finished.connect(loop.quit)
    guard = QTimer()
    guard.setSingleShot(True)
    guard.timeout.connect(loop.quit)
    guard.start(timeout_ms)
    fetcher.start()
    loop.exec()
    assert fetcher.isFinished(), "fetcher did not finish within the timeout"


class _FakeResponse:
    """Stands in for the object urllib.request.urlopen() yields as a context manager."""

    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_rates_ready_emits_decimal_rates_and_date(qapp, monkeypatch):
    payload = json.dumps({
        "amount": 1.0, "base": "USD", "date": "2026-08-15",
        "rates": {"EUR": 0.9234, "GBP": 0.789},
    }).encode("utf-8")
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda url, timeout=None: _FakeResponse(payload)
    )

    fetcher = RatesFetcher("USD")
    got: dict = {}
    fetcher.rates_ready.connect(lambda rates, d: got.update(rates=rates, date=d))
    _run_to_finish(fetcher)

    assert got["date"] == "2026-08-15"
    assert got["rates"]["EUR"] == Decimal("0.9234")
    assert got["rates"]["GBP"] == Decimal("0.789")
    assert got["rates"]["USD"] == Decimal("1")  # base is added locally, not in the API payload


def test_fetch_error_emitted_on_network_failure(qapp, monkeypatch):
    def boom(url, timeout=None):
        raise OSError("network down")

    monkeypatch.setattr(urllib.request, "urlopen", boom)

    fetcher = RatesFetcher("USD")
    errors: list = []
    fetcher.fetch_error.connect(errors.append)
    _run_to_finish(fetcher)

    assert len(errors) == 1
    assert "connection" in errors[0].lower()


def test_fetch_error_emitted_on_malformed_response(qapp, monkeypatch):
    # Missing the "rates" key entirely -- a real-world API-shape-change case,
    # distinct from a network-level failure but must fail the same safe way.
    monkeypatch.setattr(
        urllib.request, "urlopen",
        lambda url, timeout=None: _FakeResponse(b'{"base": "USD"}'),
    )

    fetcher = RatesFetcher("USD")
    errors: list = []
    fetcher.fetch_error.connect(errors.append)
    _run_to_finish(fetcher)

    assert len(errors) == 1


def test_stop_fetcher_safe_on_none_and_not_running(qapp):
    stop_fetcher(None)  # must not raise
    fetcher = RatesFetcher("USD")  # never started
    stop_fetcher(fetcher)  # isRunning() is False -> no-op, must not raise
