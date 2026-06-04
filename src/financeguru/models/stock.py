from dataclasses import dataclass
from typing import Optional


@dataclass
class Stock:
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: str
    notes: Optional[str] = None
    id: Optional[int] = None
