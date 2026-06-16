import math
import sys
import traceback
from typing import Callable, TypeVar

from PySide6.QtCore import QThread, Signal

_T = TypeVar("_T")

# Shown to the user on any fetch failure. The raw exception (which can include
# URLs, hostnames, and proxy details) is logged to stderr instead of the UI.
_FETCH_ERROR_MSG = "Could not fetch market data. Check your connection and try again."

# Per-request socket timeout (connect + read), in seconds. yfinance passes its
# own 30s default to every request and re-fetches cookies/crumbs, so one
# high-level call can issue several requests. Capping the timeout here bounds how
# long any single blocking network call can run, so a stalled Yahoo endpoint
# unwinds promptly — including when the window is closed mid-fetch — instead of
# pinning the worker thread until the process exits.
_REQUEST_TIMEOUT_S = 8.0


def _make_session():
    """A curl_cffi session preserving yfinance's Chrome impersonation while
    forcing a short per-request socket timeout.

    yfinance defaults to a curl_cffi ``Session(impersonate="chrome")`` (the
    impersonation is what keeps Yahoo from blocking the requests) and passes
    ``timeout=30`` explicitly on every request, which overrides any session-level
    default. We subclass the session to *cap* that timeout instead, so the native
    socket timeout — not a wrapper thread — bounds every call. This is what lets
    us drop the old daemon-thread timeout and the leak that came with it.
    """
    from curl_cffi import requests as _creq

    class _CappedSession(_creq.Session):
        def request(self, *args, **kwargs):
            t = kwargs.get("timeout")
            kwargs["timeout"] = (
                _REQUEST_TIMEOUT_S if t is None else min(t, _REQUEST_TIMEOUT_S)
            )
            return super().request(*args, **kwargs)

    return _CappedSession(impersonate="chrome")


def _safe_call(fn: Callable[[], _T]) -> tuple[bool, _T | None]:
    """Run fn() directly, returning ``(ok, value)``.

    ``ok`` is True only when fn() ran to completion; it is False if it raised.
    This lets the caller tell a genuine "no data" result (ok=True, value=None)
    apart from a fetch that failed (ok=False), so per-ticker network or
    rate-limit failures can be surfaced instead of silently blanking a value.

    yfinance now applies its own socket timeout (capped via :func:`_make_session`),
    so a stalled fetch raises rather than hanging — no wrapper thread is needed to
    bound it, and a timeout surfaces here as ``ok=False``.
    """
    try:
        return True, fn()
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return False, None


class PriceFetcher(QThread):
    prices_ready = Signal(dict)   # {ticker: float | None}
    fetch_error = Signal(str)
    partial_error = Signal(list)  # [ticker, ...] that timed out or errored

    def __init__(self, tickers: list[str], parent=None):
        super().__init__(parent)
        self._tickers = tickers

    def run(self) -> None:
        try:
            import yfinance as yf
            session = _make_session()
            prices: dict[str, float | None] = {}
            failed: list[str] = []
            for ticker in self._tickers:
                ok, value = _safe_call(
                    lambda t=ticker: self._fetch_price(yf, t, session)
                )
                prices[ticker] = value if ok else None
                if not ok:
                    failed.append(ticker)
            self.prices_ready.emit(prices)
            if failed:
                self.partial_error.emit(failed)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.fetch_error.emit(_FETCH_ERROR_MSG)

    @staticmethod
    def _fetch_price(yf, ticker: str, session) -> float | None:
        # Coerce and sanity-check the network value: yfinance can return None,
        # NaN, or absurd numbers for delisted/bad tickers, which would otherwise
        # propagate silently into market-value and gain/loss as "nan".
        lp = float(yf.Ticker(ticker, session=session).fast_info.last_price)
        return lp if math.isfinite(lp) and lp > 0 else None


# {ticker: {"action": str|None, "target": float|None, "count": int|None}}
TipData = dict[str, dict]


class TipFetcher(QThread):
    tips_ready = Signal(dict)
    fetch_error = Signal(str)
    partial_error = Signal(list)  # [ticker, ...] that timed out or errored

    def __init__(self, tickers: list[str], parent=None):
        super().__init__(parent)
        self._tickers = tickers

    def run(self) -> None:
        try:
            import yfinance as yf
            session = _make_session()
            result: TipData = {}
            failed: list[str] = []
            for ticker in self._tickers:
                ok, value = _safe_call(
                    lambda t=ticker: self._fetch_one(yf.Ticker(t, session=session))
                )
                if ok and value is not None:
                    fetch_failed, data = value
                else:
                    fetch_failed, data = True, None
                result[ticker] = data or {"action": None, "target": None, "count": None}
                if fetch_failed:
                    failed.append(ticker)
            self.tips_ready.emit(result)
            if failed:
                self.partial_error.emit(failed)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.fetch_error.emit(_FETCH_ERROR_MSG)

    @staticmethod
    def _fetch_one(t) -> tuple[bool, dict]:
        """Return ``(failed, data)``.

        ``failed`` is True when a network fetch errored (e.g. a capped-timeout or
        rate-limit), as opposed to a ticker that simply has no analyst coverage
        (no error, just empty data). Each field is fetched independently so one
        missing field doesn't blank the other; an error in either marks the
        ticker failed so the view can name it to the user.
        """
        action = None
        target = None
        count = None
        failed = False
        try:
            pts = t.analyst_price_targets
            if pts and pts.get("mean"):
                mean = float(pts["mean"])
                # Reject NaN/inf/non-positive so they don't reach the UI as "nan".
                target = mean if math.isfinite(mean) and mean > 0 else None
        except Exception:
            traceback.print_exc(file=sys.stderr)
            failed = True
        try:
            summary = t.recommendations_summary
            if summary is not None and not summary.empty:
                # prefer current-month row, else most recent
                row = summary[summary["period"] == "0m"]
                if row.empty:
                    row = summary.iloc[[0]]
                row = row.iloc[0]
                strong_buy = int(row.get("strongBuy", 0))
                buy = int(row.get("buy", 0))
                hold = int(row.get("hold", 0))
                sell = int(row.get("sell", 0))
                strong_sell = int(row.get("strongSell", 0))
                count = strong_buy + buy + hold + sell + strong_sell
                scores = {
                    "Strong Buy": strong_buy * 2,
                    "Buy": buy * 1,
                    "Hold": hold * 0,
                    "Sell": sell * -1,
                    "Strong Sell": strong_sell * -2,
                }
                if count:
                    weighted = sum(scores.values()) / count
                    if weighted >= 1.0:
                        action = "Strong Buy"
                    elif weighted >= 0.4:
                        action = "Buy"
                    elif weighted >= -0.4:
                        action = "Hold"
                    elif weighted >= -1.0:
                        action = "Sell"
                    else:
                        action = "Strong Sell"
        except Exception:
            traceback.print_exc(file=sys.stderr)
            failed = True
        return failed, {"action": action, "target": target, "count": count}
