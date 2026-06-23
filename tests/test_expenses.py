from decimal import Decimal

from financeguru.models.expense import Expense
from financeguru.repositories import expenses


def test_add_and_get_all_roundtrips_decimal_and_category():
    expenses.add(Expense(amount=Decimal("42.50"), spent_date="2026-06-01",
                         category="Food", notes="lunch"))
    rows = expenses.get_all()
    assert len(rows) == 1
    e = rows[0]
    assert e.amount == Decimal("42.50")
    assert isinstance(e.amount, Decimal)
    assert e.category == "Food"
    assert e.notes == "lunch"


def test_default_category_is_other():
    expenses.add(Expense(amount=Decimal("5"), spent_date="2026-06-01"))
    assert expenses.get_all()[0].category == "Other"


def test_get_all_orders_by_spent_date_desc():
    expenses.add(Expense(amount=Decimal("1"), spent_date="2026-01-01"))
    expenses.add(Expense(amount=Decimal("2"), spent_date="2026-03-01"))
    expenses.add(Expense(amount=Decimal("3"), spent_date="2026-02-01"))
    assert [e.spent_date for e in expenses.get_all()] == \
        ["2026-03-01", "2026-02-01", "2026-01-01"]


def test_update_and_delete():
    eid = expenses.add(Expense(amount=Decimal("10"), spent_date="2026-06-01",
                               category="Food"))
    assert eid
    expenses.update(Expense(id=eid, amount=Decimal("12.25"), spent_date="2026-06-02",
                            category="Transport", notes="bus"))
    e = expenses.get_all()[0]
    assert e.amount == Decimal("12.25")
    assert e.spent_date == "2026-06-02"
    assert e.category == "Transport"
    assert e.notes == "bus"

    expenses.delete(eid)
    assert expenses.get_all() == []


def test_total_for_month_sums_only_that_month():
    expenses.add(Expense(amount=Decimal("40.00"), spent_date="2026-06-03"))
    expenses.add(Expense(amount=Decimal("12.50"), spent_date="2026-06-20"))
    expenses.add(Expense(amount=Decimal("99.99"), spent_date="2026-05-31"))
    expenses.add(Expense(amount=Decimal("1.00"), spent_date="2026-07-01"))
    total = expenses.total_for_month(2026, 6)
    assert total == Decimal("52.50")
    assert isinstance(total, Decimal)


def test_total_for_month_is_zero_when_no_expenses():
    assert expenses.total_for_month(2026, 6) == Decimal("0")
