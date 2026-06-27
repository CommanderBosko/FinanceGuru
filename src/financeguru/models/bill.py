from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from financeguru.categories import DEFAULT_CATEGORY


@dataclass
class Bill:
    name: str
    amount: Decimal
    due_day: int
    # Calendar month (1-12) a yearly or one-time bill falls due. None for
    # monthly bills, which are due every month.
    due_month: Optional[int] = None
    # Calendar year a one-time bill falls due. None for monthly/yearly bills,
    # which recur and so aren't pinned to a single year.
    due_year: Optional[int] = None
    recurrence: str = "monthly"
    is_active: bool = True
    notes: Optional[str] = None
    category: str = DEFAULT_CATEGORY
    id: Optional[int] = None

    def is_due_in(self, year: int, month: int) -> bool:
        """Whether this bill's schedule places it in the given calendar month.

        Ignores active state and payment status — purely about recurrence:
        monthly bills are due every month, yearly bills in their ``due_month``,
        and a one-time bill only in its exact ``due_year``/``due_month``.
        """
        if self.recurrence == "monthly":
            return True
        if self.recurrence == "yearly":
            return self.due_month == month
        if self.recurrence == "one-time":
            return self.due_year == year and self.due_month == month
        return False
