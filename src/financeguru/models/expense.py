from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from financeguru.categories import DEFAULT_CATEGORY


@dataclass
class Expense:
    amount: Decimal
    spent_date: str
    category: str = DEFAULT_CATEGORY
    notes: Optional[str] = None
    id: Optional[int] = None
