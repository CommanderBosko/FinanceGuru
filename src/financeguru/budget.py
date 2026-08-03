"""Normalization helpers for turning bills into monthly figures."""
from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.money import ZERO


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
