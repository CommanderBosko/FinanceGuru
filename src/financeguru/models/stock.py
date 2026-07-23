from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Stock:
    ticker: str
    shares: Decimal
    purchase_price: Decimal
    purchase_date: str
    notes: str | None = None
    # Most recent fetched market price and the ISO date it was fetched,
    # persisted so net-worth snapshots can value the position without a
    # network call. None until the first successful price refresh.
    last_price: Decimal | None = None
    last_price_date: str | None = None
    id: int | None = None
