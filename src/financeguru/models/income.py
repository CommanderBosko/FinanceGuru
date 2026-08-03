from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Income:
    name: str          # e.g. "Bosko — Main Job", "Natty — Salary"
    amount: Decimal    # amount received each month
    pay_day: int       # day of month (1-31) the paycheck lands
    notes: str | None = None
    id: int | None = None
