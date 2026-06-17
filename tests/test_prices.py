"""Tests for the fetch plumbing in prices.py.

The fetchers themselves are QThreads that hit the network, but the per-ticker
success/failure decision lives in `_safe_call`, which is pure and fast to test.
This is what lets the views tell a genuine empty result apart from a fetch that
errored. `_make_session` is also covered: it must cap the per-request socket
timeout, which is what bounds a blocking call (replacing the old daemon-thread
timeout) so a stalled fetch can't pin the worker thread.
"""
import time

import pytest

from financeguru import prices
from financeguru.prices import (
    PriceFetcher,
    TipFetcher,
    _REQUEST_TIMEOUT_S,
    _safe_call,
    stop_fetcher,
)


def test_returns_ok_with_value_on_success():
    ok, value = _safe_call(lambda: 42)
    assert ok is True
    assert value == 42


def test_success_with_none_value_is_still_ok():
    # A function that legitimately returns None (e.g. a delisted ticker) is a
    # success, not a failure — ok must be True so the view doesn't warn.
    ok, value = _safe_call(lambda: None)
    assert ok is True
    assert value is None


def test_exception_is_reported_as_failure():
    def boom():
        raise RuntimeError("network down")

    ok, value = _safe_call(boom)
    assert ok is False
    assert value is None


# _make_session pulls in curl_cffi, which only exists inside `nix develop`.
pytest.importorskip("curl_cffi")


def _capture_request_timeout(monkeypatch, **request_kwargs):
    """Build a session and record the timeout it forwards to the base session."""
    from curl_cffi import requests as creq

    from financeguru.prices import _make_session

    captured = {}

    def fake_request(self, *args, timeout=None, **kwargs):
        captured["timeout"] = timeout
        return "ok"

    monkeypatch.setattr(creq.Session, "request", fake_request)
    session = _make_session()
    session.request("GET", "https://example.com", **request_kwargs)
    return captured["timeout"]


def test_session_caps_an_explicit_timeout(monkeypatch):
    # yfinance passes timeout=30 explicitly; the session must clamp it down so
    # the native socket timeout bounds every request.
    assert _capture_request_timeout(monkeypatch, timeout=30) == _REQUEST_TIMEOUT_S


def test_session_applies_cap_when_no_timeout_given(monkeypatch):
    assert _capture_request_timeout(monkeypatch) == _REQUEST_TIMEOUT_S


def test_session_keeps_a_shorter_timeout(monkeypatch):
    # A caller asking for less than the cap should not be raised up to it.
    assert _capture_request_timeout(monkeypatch, timeout=1.0) == 1.0


# ---- Fetcher QThread behaviour (signals + cancel/stop) ----
#
# These exercise the _TickerFetcher hierarchy end to end: the cancel flag, the
# refactored signal emission on the subclasses, and stop_fetcher's teardown
# contract. The network is stubbed out so they're fast and deterministic.

from PySide6.QtCore import QCoreApplication, QEventLoop, QTimer


@pytest.fixture
def qapp():
    # QThread signals are delivered via the event loop, so a (non-GUI) app must
    # exist. Reuse one across tests; QCoreApplication is a process singleton.
    return QCoreApplication.instance() or QCoreApplication([])


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


def test_price_fetcher_emits_prices_and_flags_failures(qapp, monkeypatch):
    monkeypatch.setattr(prices, "_make_session", lambda: object())

    def fake_fetch(yf, ticker, session):
        if ticker == "BAD":
            raise RuntimeError("network down")
        return 123.45 if ticker == "AAPL" else None

    monkeypatch.setattr(PriceFetcher, "_fetch_price", staticmethod(fake_fetch))

    fetcher = PriceFetcher(["AAPL", "DELISTED", "BAD"])
    prices_out: dict = {}
    partials: list = []
    fetcher.prices_ready.connect(prices_out.update)
    fetcher.partial_error.connect(partials.extend)
    _run_to_finish(fetcher)

    # A real value, a legit no-data None (ok), and an errored ticker (None + flagged).
    assert prices_out == {"AAPL": 123.45, "DELISTED": None, "BAD": None}
    assert partials == ["BAD"]


def test_tip_fetcher_emits_and_marks_failures(qapp, monkeypatch):
    import types

    import yfinance

    monkeypatch.setattr(prices, "_make_session", lambda: object())
    # run() builds yf.Ticker(symbol, session=...) and hands it to _fetch_one;
    # stub both so no network is touched and the symbol is recoverable.
    monkeypatch.setattr(
        yfinance, "Ticker", lambda t, session=None: types.SimpleNamespace(ticker=t)
    )

    def fake_one(ticker_obj):
        sym = ticker_obj.ticker
        if sym == "BAD":
            return True, None
        if sym == "NOCOVER":
            return False, {"action": None, "target": None, "count": None}
        return False, {"action": "Buy", "target": 200.0, "count": 7}

    monkeypatch.setattr(TipFetcher, "_fetch_one", staticmethod(fake_one))

    fetcher = TipFetcher(["AAPL", "NOCOVER", "BAD"])
    tips_out: dict = {}
    partials: list = []
    fetcher.tips_ready.connect(tips_out.update)
    fetcher.partial_error.connect(partials.extend)
    _run_to_finish(fetcher)

    assert tips_out["AAPL"] == {"action": "Buy", "target": 200.0, "count": 7}
    assert tips_out["NOCOVER"] == {"action": None, "target": None, "count": None}
    # An errored ticker is blanked AND named in the partial-failure list.
    assert tips_out["BAD"] == {"action": None, "target": None, "count": None}
    assert partials == ["BAD"]


def test_cancelled_before_start_emits_no_results(qapp, monkeypatch):
    monkeypatch.setattr(prices, "_make_session", lambda: object())
    monkeypatch.setattr(PriceFetcher, "_fetch_price", staticmethod(lambda yf, t, s: 1.0))

    fetcher = PriceFetcher(["AAPL", "MSFT"])
    fetcher.cancel()  # the loop's top-of-iteration guard must short-circuit
    emitted: list = []
    fetcher.prices_ready.connect(emitted.append)
    _run_to_finish(fetcher)

    assert emitted == []


def test_stop_fetcher_cancels_a_running_fetch(qapp, monkeypatch):
    monkeypatch.setattr(prices, "_make_session", lambda: object())
    started: list = []

    def slow_fetch(yf, ticker, session):
        started.append(ticker)
        time.sleep(0.02)
        return 1.0

    monkeypatch.setattr(PriceFetcher, "_fetch_price", staticmethod(slow_fetch))

    fetcher = PriceFetcher([f"T{i}" for i in range(200)])
    fetcher.start()

    deadline = time.monotonic() + 10
    while not started and time.monotonic() < deadline:
        time.sleep(0.001)
    assert started, "worker never started"

    stop_fetcher(fetcher)  # cancels and waits for the run loop to unwind

    assert fetcher.isFinished()
    assert len(started) < 200  # stopped well before processing every ticker


def test_stop_fetcher_safe_on_none_and_not_running(qapp):
    stop_fetcher(None)  # must not raise
    fetcher = PriceFetcher(["AAPL"])  # never started
    stop_fetcher(fetcher)  # isRunning() is False -> no-op, must not raise
