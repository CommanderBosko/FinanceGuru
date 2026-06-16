from decimal import Decimal

from financeguru.budget import (
    SPECIFIC_DAYS,
    format_pay_days,
    monthly_bill,
    monthly_income,
    parse_pay_days,
)
from financeguru.models.bill import Bill
from financeguru.models.income import Income


def _income(amount, frequency, pay_days=None) -> Income:
    return Income(name="Job", amount=Decimal(amount), frequency=frequency, pay_days=pay_days)


def test_parse_pay_days_filters_and_sorts():
    assert parse_pay_days("15, 1, 1, 40, abc, 31") == [1, 15, 31]
    assert parse_pay_days(None) == []
    assert parse_pay_days("") == []
    assert parse_pay_days("0, 32") == []  # out of 1-31 range


def test_format_pay_days_is_human_readable():
    assert format_pay_days("15,1") == "1, 15"
    assert format_pay_days(None) == ""


def test_monthly_income_exact_frequencies():
    assert monthly_income(_income("1000", "monthly")) == Decimal("1000")
    assert monthly_income(_income("12000", "annual")) == Decimal("1000")
    assert monthly_income(_income("1000", "semimonthly")) == Decimal("2000")
    assert monthly_income(_income("120", "weekly")) == Decimal("120") * 52 / 12
    assert monthly_income(_income("120", "biweekly")) == Decimal("120") * 26 / 12


def test_monthly_income_specific_days_multiplies_by_day_count():
    inc = _income("500", SPECIFIC_DAYS, pay_days="1, 15")
    assert monthly_income(inc) == Decimal("1000")
    # No selected days means no income from this source.
    assert monthly_income(_income("500", SPECIFIC_DAYS, pay_days=None)) == Decimal("0")


def test_monthly_income_unknown_frequency_falls_back_to_monthly():
    assert monthly_income(_income("750", "fortnightly")) == Decimal("750")


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
