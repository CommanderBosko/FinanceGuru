from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Payment:
    amount: Decimal
    paid_date: str
    bill_id: Optional[int] = None
    notes: Optional[str] = None
    id: Optional[int] = None
