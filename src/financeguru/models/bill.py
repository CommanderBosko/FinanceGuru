from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Bill:
    name: str
    amount: Decimal
    due_day: int
    recurrence: str = "monthly"
    is_active: bool = True
    notes: Optional[str] = None
    id: Optional[int] = None
