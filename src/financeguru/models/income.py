from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Income:
    name: str          # e.g. "Bosko — Main Job", "Natty — Salary"
    amount: Decimal    # amount per pay period
    frequency: str     # weekly, biweekly, semimonthly, monthly, annual, specific days
    pay_days: str | None = None  # comma-separated days of month, for "specific days"
    notes: str | None = None
    id: int | None = None
