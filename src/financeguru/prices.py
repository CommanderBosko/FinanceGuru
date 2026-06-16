import math
import sys
import threading
import traceback
from typing import Callable, TypeVar

from PySide6.QtCore import QThread, Signal

_T = TypeVar("_T")

# Shown to the user on any fetch failure. The raw exception (which can include
# URLs, hostnames, and proxy details) is logged to stderr instead of the UI.
_FETCH_ERROR_MSG = "Could not fetch market data. Check your connection and try again."

# Hard cap on a single ticker fetch. yfinance/requests can hang on a slow or
# unresponsive Yahoo endpoint with no timeout of its own; without this bound a
# stuck network call would leave the Refresh button disabled ("Fetching…")
# forever, recoverable only by restarting the app.
_FETCH_TIMEOUT_S = 15.0


def _call_with_timeout(fn: Callable[[], _T], timeout: float) -> tuple[bool, _T | None]:
    """Run fn() in a daemon thread, returning ``(ok, value)``.

    ``ok`` is True only when fn() ran to completion; it is False on a timeout or
    an exception. This lets the caller tell a genuine "no data" result (ok=True,
    value=None) apart from a fetch that failed (ok=False), so per-ticker network
    or rate-limit failures can be surfaced instead of silently blanking a value.

    Guarantees the caller is never blocked longer than `timeout`, so the
    surrounding fetch loop always makes progress and emits a result.
    """
    box: dict = {}

    def target():
        try:
            box["value"] = fn()
            box["ok"] = True
        except Exception:
            traceback.print_exc(file=sys.stderr)

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout)
    return box.get("ok", False), box.get("value")


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
            prices: dict[str, float | None] = {}
            failed: list[str] = []
            for ticker in self._tickers:
                ok, value = _call_with_timeout(
                    lambda t=ticker: self._fetch_price(yf, t), _FETCH_TIMEOUT_S
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
    def _fetch_price(yf, ticker: str) -> float | None:
        # Coerce and sanity-check the network value: yfinance can return None,
        # NaN, or absurd numbers for delisted/bad tickers, which would otherwise
        # propagate silently into market-value and gain/loss as "nan".
        lp = float(yf.Ticker(ticker).fast_info.last_price)
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
            result: TipData = {}
            failed: list[str] = []
            for ticker in self._tickers:
                ok, data = _call_with_timeout(
                    lambda t=ticker: self._fetch_one(yf.Ticker(t)), _FETCH_TIMEOUT_S
                )
                result[ticker] = data or {"action": None, "target": None, "count": None}
                if not ok:
                    failed.append(ticker)
            self.tips_ready.emit(result)
            if failed:
                self.partial_error.emit(failed)
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.fetch_error.emit(_FETCH_ERROR_MSG)

    @staticmethod
    def _fetch_one(t) -> dict:
        action = None
        target = None
        count = None
        try:
            pts = t.analyst_price_targets
            if pts and pts.get("mean"):
                mean = float(pts["mean"])
                # Reject NaN/inf/non-positive so they don't reach the UI as "nan".
                target = mean if math.isfinite(mean) and mean > 0 else None
        except Exception:
            pass
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
            pass
        return {"action": action, "target": target, "count": count}
