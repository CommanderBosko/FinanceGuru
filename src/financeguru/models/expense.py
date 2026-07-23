from dataclasses import dataclass
from decimal import Decimal

from financeguru.categories import DEFAULT_CATEGORY


@dataclass
class Expense:
    amount: Decimal
    spent_date: str
    category: str = DEFAULT_CATEGORY
    notes: str | None = None
    id: int | None = None
