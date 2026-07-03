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

    def overdue_carryover_start(self, year: int, month: int) -> str | None:
        """First-of-month ISO date ("YYYY-MM-01") of this bill's most recent
        missed-able due cycle strictly before the given month, or None.

        Purely about recurrence — ignores active state and payment status
        (whether the cycle was actually paid is the caller's concern).
        """
        if self.recurrence == "yearly":
            # Carryover is limited to the current calendar year: a freshly
            # added yearly bill whose season hasn't come yet this year must
            # not show as Overdue, so previous years never carry over (an
            # unpaid December yearly drops off in January — accepted
            # trade-off).
            if self.due_month is not None and self.due_month < month:
                return f"{year}-{self.due_month:02d}-01"
            return None
        if self.recurrence == "one-time":
            # Carries across year boundaries — the user explicitly entered
            # this date, so it stays overdue until paid.
            if (self.due_year is not None and self.due_month is not None
                    and (self.due_year, self.due_month) < (year, month)):
                return f"{self.due_year}-{self.due_month:02d}-01"
            return None
        # Monthly bills are due every month and are already covered by the
        # current-month logic.
        return None
