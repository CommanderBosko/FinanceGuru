from dataclasses import dataclass
from datetime import date
from decimal import ROUND_UP, Decimal
from typing import Optional

from financeguru.money import CENT


def months_remaining(target_date: str, today: date | None = None) -> int:
    """Number of monthly contributions left to reach a goal by ``target_date``.

    Counts whole calendar months between today's month and the target month,
    floored at 1 so a goal due this month (or already past) still yields a single
    contribution rather than a divide-by-zero.
    """
    today = today or date.today()
    target = date.fromisoformat(target_date)
    months = (target.year - today.year) * 12 + (target.month - today.month)
    return max(months, 1)


@dataclass
class Goal:
    name: str
    price: Decimal
    target_date: str          # ISO yyyy-mm-dd — when you want to afford it
    notes: Optional[str] = None
    bill_id: Optional[int] = None   # the auto-created "Goal" bill that saves for it
    id: Optional[int] = None

    def monthly_savings(self, today: date | None = None) -> Decimal:
        """Amount to set aside each month to afford the goal by its target date.

        Rounded up to the cent so the contributions always fully fund the price.
        """
        months = months_remaining(self.target_date, today)
        return (self.price / months).quantize(CENT, rounding=ROUND_UP)
