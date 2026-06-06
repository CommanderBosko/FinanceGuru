"""Normalization helpers for turning incomes and bills into monthly figures."""
from financeguru.models.bill import Bill
from financeguru.models.income import Income

# Frequency value for "paid on specific calendar days of the month".
SPECIFIC_DAYS = "specific days"

# Pay frequencies and how many times they occur per month, on average.
INCOME_FREQUENCIES = ["weekly", "biweekly", "semimonthly", "monthly", "annual", SPECIFIC_DAYS]

_MONTHLY_FACTOR = {
    "weekly": 52 / 12,        # 52 paychecks / 12 months
    "biweekly": 26 / 12,      # 26 paychecks / 12 months
    "semimonthly": 2.0,       # twice a month
    "monthly": 1.0,
    "annual": 1 / 12,
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


def monthly_income(income: Income) -> float:
    """Income amount expressed as a per-month figure."""
    if income.frequency == SPECIFIC_DAYS:
        # One paycheck of `amount` on each selected day of the month.
        return income.amount * len(parse_pay_days(income.pay_days))
    return income.amount * _MONTHLY_FACTOR.get(income.frequency, 1.0)


def monthly_bill(bill: Bill) -> float:
    """Active bill cost expressed as a per-month figure.

    Yearly bills are spread across 12 months; one-time bills are not a
    recurring monthly obligation and are excluded.
    """
    if not bill.is_active:
        return 0.0
    if bill.recurrence == "yearly":
        return bill.amount / 12
    if bill.recurrence == "one-time":
        return 0.0
    return bill.amount  # monthly
