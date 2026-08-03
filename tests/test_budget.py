from decimal import Decimal

from financeguru.budget import monthly_bill
from financeguru.models.bill import Bill


def test_monthly_bill_by_recurrence():
    assert monthly_bill(Bill(name="Rent", amount=Decimal("1200"), due_day=1)) == Decimal("1200")
    assert monthly_bill(
        Bill(name="Insurance", amount=Decimal("1200"), due_day=1, recurrence="yearly")
    ) == Decimal("100")
    assert monthly_bill(
        Bill(name="Couch", amount=Decimal("900"), due_day=1, recurrence="one-time")
    ) == Decimal("0")


def test_monthly_bill_inactive_is_zero():
    bill = Bill(name="Gym", amount=Decimal("40"), due_day=1, is_active=False)
    assert monthly_bill(bill) == Decimal("0")
