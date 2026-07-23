from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Payment:
    amount: Decimal
    paid_date: str
    bill_id: int | None = None
    notes: str | None = None
    id: int | None = None
