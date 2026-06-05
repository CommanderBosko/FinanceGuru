"""Normalization helpers for turning incomes and bills into monthly figures."""
from financeguru.models.bill import Bill
from financeguru.models.income import Income

# Pay frequencies and how many times they occur per month, on average.
INCOME_FREQUENCIES = ["weekly", "biweekly", "semimonthly", "monthly", "annual"]

_MONTHLY_FACTOR = {
    "weekly": 52 / 12,        # 52 paychecks / 12 months
    "biweekly": 26 / 12,      # 26 paychecks / 12 months
    "semimonthly": 2.0,       # twice a month
    "monthly": 1.0,
    "annual": 1 / 12,
}


def monthly_income(income: Income) -> float:
    """Income amount expressed as a per-month figure."""
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
