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
    id: Optional[int] = None
