from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Stock:
    ticker: str
    shares: Decimal
    purchase_price: Decimal
    purchase_date: str
    notes: Optional[str] = None
    # Most recent fetched market price and the ISO date it was fetched,
    # persisted so net-worth snapshots can value the position without a
    # network call. None until the first successful price refresh.
    last_price: Optional[Decimal] = None
    last_price_date: Optional[str] = None
    id: Optional[int] = None
