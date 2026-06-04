from dataclasses import dataclass
from typing import Optional


@dataclass
class Payment:
    amount: float
    paid_date: str
    bill_id: Optional[int] = None
    notes: Optional[str] = None
    id: Optional[int] = None
