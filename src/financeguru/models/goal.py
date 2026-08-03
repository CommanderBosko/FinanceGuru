from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_UP, Decimal

from financeguru.money import CENT


def months_remaining(target_date: str, today: date | None = None) -> int:
    """Number of monthly contributions between ``today`` and ``target_date``.

    Counts whole calendar months between the reference month and the target
    month, floored at 1 so a goal due that same month (or already past) still
    yields a single contribution rather than a divide-by-zero. ``today`` is
    just the reference point — callers pass either the real current date or a
    goal's ``start_date`` depending on what they're measuring.
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
    start_date: str = field(default_factory=lambda: date.today().isoformat())
    notes: str | None = None
    bill_id: int | None = None   # the auto-created "Goal" bill that saves for it
    id: int | None = None

    def monthly_savings(self) -> Decimal:
        """Amount to set aside each month to afford the goal by its target date.

        Fixed over the start_date -> target_date span so the required
        contribution doesn't drift as real "today" advances — it only
        changes if the goal itself is edited. Rounded up to the cent so the
        contributions always fully fund the price.
        """
        start = date.fromisoformat(self.start_date)
        months = months_remaining(self.target_date, start)
        return (self.price / months).quantize(CENT, rounding=ROUND_UP)
