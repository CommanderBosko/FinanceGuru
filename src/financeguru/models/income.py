from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class Income:
    name: str          # e.g. "Bosko — Main Job", "Natty — Salary"
    amount: Decimal    # amount per pay period
    frequency: str     # weekly, biweekly, semimonthly, monthly, annual, specific days
    pay_days: Optional[str] = None  # comma-separated days of month, for "specific days"
    notes: Optional[str] = None
    id: Optional[int] = None
