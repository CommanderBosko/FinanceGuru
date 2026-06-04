from dataclasses import dataclass


@dataclass
class Debt:
    id: int
    name: str
    balance: float
    interest_rate: float   # APR as a percentage, e.g. 18.5
    minimum_payment: float
    notes: str | None
