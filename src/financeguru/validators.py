"""Input validators for user-supplied data that crosses a trust boundary."""

import re

# Tickers are sent to yfinance (network) and stored in the DB. Allow the common
# real-world formats for tradeable positions — letters, digits, dot, hyphen
# (e.g. AAPL, BRK.B, BF-B) — capped at 12 chars. Anything else is rejected
# before it can be embedded in an outbound request URL or persisted.
_TICKER_RE = re.compile(r"[A-Z0-9][A-Z0-9.\-]{0,11}")


def normalize_ticker(raw: str) -> str | None:
    """Strip/upper a ticker and return it if it matches an allowed format, else None."""
    ticker = raw.strip().upper()
    return ticker if _TICKER_RE.fullmatch(ticker) else None
