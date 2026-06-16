from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Expense:
    amount: Decimal
    spent_date: str
    category: str = "Other"
    notes: Optional[str] = None
    id: Optional[int] = None
