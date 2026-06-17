from datetime import date
from decimal import Decimal

from financeguru import reporting
from financeguru.models.bill import Bill
from financeguru.models.expense import Expense
from financeguru.models.goal import Goal
from financeguru.models.payment import Payment
from financeguru.repositories import bills, expenses, goals, payments


def _this_month_date(day: int = 15) -> str:
    today = date.today()
    return f"{today.year}-{today.month:02d}-{day:02d}"


# ---- category_breakdown (explicit month, independent of "today") ----

def test_payment_inherits_bill_category():
    bid = bills.add(Bill(name="Rent", amount=Decimal("1200"), due_day=1,
                         category="Housing"))
    payments.add(Payment(amount=Decimal("1200"), paid_date="2026-06-01", bill_id=bid))
    assert reporting.category_breakdown(2026, 6) == {"Housing": 1200.0}


def test_goal_payment_is_savings_via_goals_fk():
    # Payments against a goal-linked bill land in Savings because of the goals
    # foreign key — even if the bill's own category says otherwise.
    bid = bills.add(Bill(name="Vacation", amount=Decimal("100"), due_day=1,
                         category="Other"))
    goals.add(Goal(name="Vacation", price=Decimal("100"),
                   target_date="2026-12-31", bill_id=bid))
    payments.add(Payment(amount=Decimal("100"), paid_date="2026-06-10", bill_id=bid))
    assert reporting.category_breakdown(2026, 6) == {"Savings": 100.0}


def test_unlinked_bill_noted_goal_is_not_savings():
    # A user's own bill whose note happens to be "Goal" must NOT be treated as a
    # goal contribution — only the goals FK does that. It keeps its category.
    bid = bills.add(Bill(name="Gym", amount=Decimal("30"), due_day=1,
                         notes="Goal", category="Health"))
    payments.add(Payment(amount=Decimal("30"), paid_date="2026-06-10", bill_id=bid))
    assert reporting.category_breakdown(2026, 6) == {"Health": 30.0}


def test_payment_without_bill_is_other():
    payments.add(Payment(amount=Decimal("25"), paid_date="2026-06-05", bill_id=None))
    assert reporting.category_breakdown(2026, 6) == {"Other": 25.0}


def test_expense_uses_its_own_category():
    expenses.add(Expense(amount=Decimal("40"), spent_date="2026-06-03",
                         category="Transport"))
    assert reporting.category_breakdown(2026, 6) == {"Transport": 40.0}


def test_breakdown_sums_payments_and_expenses_per_category():
    bid = bills.add(Bill(name="Groceries", amount=Decimal("0"), due_day=1,
                         category="Food"))
    payments.add(Payment(amount=Decimal("60"), paid_date="2026-06-02", bill_id=bid))
    expenses.add(Expense(amount=Decimal("15.50"), spent_date="2026-06-04",
                         category="Food"))
    expenses.add(Expense(amount=Decimal("40"), spent_date="2026-06-04",
                         category="Transport"))
    assert reporting.category_breakdown(2026, 6) == {"Food": 75.5, "Transport": 40.0}


def test_breakdown_respects_month_boundaries():
    expenses.add(Expense(amount=Decimal("10"), spent_date="2026-05-31",
                         category="Food"))
    expenses.add(Expense(amount=Decimal("20"), spent_date="2026-06-30",
                         category="Food"))
    expenses.add(Expense(amount=Decimal("30"), spent_date="2026-07-01",
                         category="Food"))
    assert reporting.category_breakdown(2026, 6) == {"Food": 20.0}


def test_breakdown_empty_month_is_empty_dict():
    assert reporting.category_breakdown(2026, 6) == {}


def test_breakdown_values_are_floats():
    expenses.add(Expense(amount=Decimal("5"), spent_date="2026-06-01",
                         category="Food"))
    (value,) = reporting.category_breakdown(2026, 6).values()
    assert isinstance(value, float)


# ---- monthly_spending (anchored to the current month) ----

def test_monthly_spending_returns_window_entries_oldest_first():
    out = reporting.monthly_spending(window=12)
    assert len(out) == 12
    labels = [e["label"] for e in out]
    assert labels == sorted(labels)
    today = date.today()
    assert out[-1]["label"] == f"{today.year}-{today.month:02d}"


def test_monthly_spending_excludes_savings_from_total():
    gid = bills.add(Bill(name="Goal", amount=Decimal("0"), due_day=1,
                         category="Savings"))
    goals.add(Goal(name="Goal", price=Decimal("500"),
                   target_date="2026-12-31", bill_id=gid))
    payments.add(Payment(amount=Decimal("500"), paid_date=_this_month_date(),
                         bill_id=gid))
    expenses.add(Expense(amount=Decimal("80"), spent_date=_this_month_date(),
                         category="Food"))

    current = reporting.monthly_spending(window=12)[-1]
    # Savings is visible in the breakdown but kept out of the headline total.
    assert current["total"] == 80.0
    assert current["by_category"]["Savings"] == 500.0
    assert current["by_category"]["Food"] == 80.0


def test_monthly_spending_zero_fills_sparse_history():
    expenses.add(Expense(amount=Decimal("12"), spent_date=_this_month_date(),
                         category="Food"))
    out = reporting.monthly_spending(window=12)
    assert out[-1]["total"] == 12.0
    # Every earlier month with no activity is present and empty.
    assert all(e["total"] == 0.0 and e["by_category"] == {} for e in out[:-1])
