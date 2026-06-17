from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Bill:
    name: str
    amount: Decimal
    due_day: int
    # Calendar month (1-12) a yearly bill falls due. None for monthly bills
    # (due every month) and one-time bills (no recurring month).
    due_month: Optional[int] = None
    recurrence: str = "monthly"
    is_active: bool = True
    notes: Optional[str] = None
    category: str = "Other"
    id: Optional[int] = None
