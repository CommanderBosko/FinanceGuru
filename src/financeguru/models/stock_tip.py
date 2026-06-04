from dataclasses import dataclass


@dataclass
class StockTip:
    id: int
    ticker: str
    action: str
    target_price: float | None
    confidence: int
    notes: str | None
    added_date: str
    analyst_action: str | None = None
    analyst_target: float | None = None
    analyst_count: int | None = None
    analyst_updated: str | None = None
