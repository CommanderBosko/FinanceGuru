from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Income:
    name: str          # e.g. "Bosko — Main Job", "Natty — Salary"
    amount: Decimal    # amount of this paycheck
    pay_date: str       # ISO date (YYYY-MM-DD) the paycheck landed
    notes: str | None = None
    id: int | None = None
