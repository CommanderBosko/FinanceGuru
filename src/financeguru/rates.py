"""Live exchange-rate fetch (network I/O) for the Currency Converter tab.

Frankfurter (https://frankfurter.dev) is a free, keyless, ECB-based rates
API — no session/impersonation dance like prices.py's yfinance+curl_cffi setup
is needed here, so a plain ``urllib`` call bounded by a socket timeout is
enough. One request (``/latest?from=<base>``) returns the full rate table, so
the converter never needs a second fetch just because the user picked a
different currency pair.

Two things the plain-urlopen version got wrong in practice, found by actually
hitting the API rather than trusting the docs:
  - The old ``api.frankfurter.app`` host now 301s to ``api.frankfurter.dev/v1``
    — call the v1 host directly rather than eating a redirect every request.
  - Cloudflare (fronting that host) 403s the default ``Python-urllib/x.y``
    User-Agent as a bot signature; a real UA string is required.
"""

import json
import sys
import traceback
from decimal import Decimal

from PySide6.QtCore import QThread, Signal

_FRANKFURTER_URL = "https://api.frankfurter.dev/v1/latest?from={base}"
_USER_AGENT = "FinanceGuru/1.0 (+https://github.com/CommanderBosko/FinanceGuru)"

# Per-request socket timeout (connect + read), in seconds.
_REQUEST_TIMEOUT_S = 8.0

# How long stop_fetcher() waits for an in-flight fetch to unwind before giving
# up on it: the request is bounded by the socket cap above, plus headroom.
_STOP_WAIT_MS = int(_REQUEST_TIMEOUT_S * 1000) + 1000

# Shown to the user on any fetch failure; the raw exception (host, proxy
# details) is logged to stderr instead, matching prices.py's convention.
_FETCH_ERROR_MSG = "Could not fetch exchange rates. Check your connection and try again."


class RatesFetcher(QThread):
    """Fetches every rate relative to ``base`` in a single background request."""

    rates_ready = Signal(dict, str)  # {code: Decimal}, rate date ("YYYY-MM-DD")
    fetch_error = Signal(str)

    def __init__(self, base: str, parent=None):
        super().__init__(parent)
        self._base = base

    def run(self) -> None:
        import urllib.request  # deferred: keeps import cost off the GUI thread's startup path

        try:
            url = _FRANKFURTER_URL.format(base=self._base)
            request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
            with urllib.request.urlopen(request, timeout=_REQUEST_TIMEOUT_S) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            rates = {code: Decimal(str(value)) for code, value in payload["rates"].items()}
            rates[self._base] = Decimal("1")  # Frankfurter omits the base from its own table
            self.rates_ready.emit(rates, payload.get("date", ""))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            self.fetch_error.emit(_FETCH_ERROR_MSG)


def stop_fetcher(fetcher: "RatesFetcher | None") -> None:
    """Block until an in-flight fetch unwinds. Safe to call with None or a
    fetcher that isn't running.

    There's nothing to cooperatively cancel mid-flight (one request, not a
    per-ticker loop like prices.py's fetchers), but the socket timeout passed
    to urlopen() only bounds the connect/send/recv phase — DNS resolution
    (getaddrinfo) has no timeout of its own and can hang past it on a
    misbehaving resolver. So, same as prices.py's stop_fetcher, the bounded
    wait falls back to an unbounded one rather than risk "QThread destroyed
    while still running" aborting the process on quit.
    """
    if fetcher is not None and fetcher.isRunning():
        if not fetcher.wait(_STOP_WAIT_MS):
            fetcher.wait()
