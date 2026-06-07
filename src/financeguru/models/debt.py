from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Debt:
    id: int
    name: str
    balance: Decimal
    interest_rate: Decimal   # APR as a percentage, e.g. 18.5
    minimum_payment: Decimal
    notes: str | None
