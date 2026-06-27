"""Normalization helpers for turning incomes and bills into monthly figures."""
import sys
from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.income import Income
from financeguru.money import ZERO

# Frequency value for "paid on specific calendar days of the month".
SPECIFIC_DAYS = "specific days"

# Pay frequencies and how many times they occur per month, on average.
INCOME_FREQUENCIES = ["weekly", "biweekly", "semimonthly", "monthly", "annual", SPECIFIC_DAYS]

# (paychecks, months) — kept as exact integer ratios so the monthly figure is
# computed with Decimal division rather than a pre-rounded float.
_MONTHLY_FACTOR = {
    "weekly": (52, 12),       # 52 paychecks / 12 months
    "biweekly": (26, 12),     # 26 paychecks / 12 months
    "semimonthly": (2, 1),    # twice a month
    "monthly": (1, 1),
    "annual": (1, 12),
}


def parse_pay_days(raw: str | None) -> list[int]:
    """Parse a comma-separated day-of-month string into sorted unique days (1-31)."""
    if not raw:
        return []
    days = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= 31:
            days.add(int(part))
    return sorted(days)


def format_pay_days(raw: str | None) -> str:
    """Human-readable list of pay days, e.g. '1, 15'."""
    return ", ".join(str(d) for d in parse_pay_days(raw))


def monthly_income(income: Income) -> Decimal:
    """Income amount expressed as a per-month figure."""
    if income.frequency == SPECIFIC_DAYS:
        # One paycheck of `amount` on each selected day of the month.
        return income.amount * len(parse_pay_days(income.pay_days))
    factor = _MONTHLY_FACTOR.get(income.frequency)
    if factor is None:
        # The UI constrains frequency to INCOME_FREQUENCIES; an unknown value
        # means bad/legacy data. Fall back to monthly but surface it rather than
        # silently mis-normalizing.
        print(f"unknown income frequency {income.frequency!r}; treating as monthly",
              file=sys.stderr)
        factor = (1, 1)
    paychecks, months = factor
    return income.amount * paychecks / months


def monthly_bill(bill: Bill) -> Decimal:
    """Active bill cost expressed as a per-month figure.

    Yearly bills are spread across 12 months; one-time bills are not a
    recurring monthly obligation and are excluded.
    """
    if not bill.is_active:
        return ZERO
    if bill.recurrence == "yearly":
        return bill.amount / 12
    if bill.recurrence == "one-time":
        return ZERO
    return bill.amount  # monthly
