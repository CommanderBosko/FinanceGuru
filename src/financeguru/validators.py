"""Input validators for user-supplied data that crosses a trust boundary."""

import re

# Tickers are sent to yfinance (network) and stored in the DB. Allow the common
# real-world formats for tradeable positions — alphanumeric groups separated by a
# single dot or hyphen (e.g. AAPL, BRK.B, BF-B). A dot/hyphen may not lead, trail,
# or repeat, so degenerate symbols like "A.." or "A--B" are rejected. Length is
# capped at 12. Anything else is rejected before it can reach a request URL or DB.
_MAX_TICKER_LEN = 12
_TICKER_RE = re.compile(r"[A-Z0-9]+(?:[.\-][A-Z0-9]+)*")


def normalize_ticker(raw: str) -> str | None:
    """Strip/upper a ticker and return it if it matches an allowed format, else None."""
    ticker = raw.strip().upper()
    if len(ticker) > _MAX_TICKER_LEN:
        return None
    return ticker if _TICKER_RE.fullmatch(ticker) else None
