from dataclasses import dataclass
from decimal import Decimal


@dataclass
class StockTip:
    id: int
    ticker: str
    action: str
    target_price: Decimal | None
    confidence: int
    notes: str | None
    added_date: str
    analyst_action: str | None = None
    analyst_target: Decimal | None = None
    analyst_count: int | None = None
    analyst_updated: str | None = None
