"""Behavioral tests for the Salary tab's month filter and budget summary.

The construction/refresh contract is covered by test_views_smoke; these tests
drive the month filter (mirroring Payments/Expenses) and the Budget summary
that sits below it — in particular, guarding against the "All" bug where
`total_bills` (always a single month's recurring obligation) used to be
subtracted straight from all-time income and expenses, producing a bogus
Extra Spending Money / Over Budget figure. SalaryView no longer owns a
month-picker widget — the global month selector in MainWindow now owns the
combo (see test_main_window_global_month.py) and drives this tab via
select_month()/select_all(); these tests exercise that same surface directly.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.expense import Expense
from financeguru.models.income import Income
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import expenses as expense_repo
from financeguru.repositories import incomes as income_repo
from financeguru.views.salary_view import SalaryView


@pytest.fixture
def view(qapp, temp_db):
    today = date.today()
    income_repo.add(Income(name="Big Job", amount=Decimal("2000.00"), pay_date=today.isoformat()))
    income_repo.add(Income(name="Side Gig", amount=Decimal("300.00"), pay_date=today.isoformat()))
    income_repo.add(Income(name="Old Job", amount=Decimal("1500.00"), pay_date="2025-01-15"))
    bill_repo.add(Bill(name="Rent", amount=Decimal("900.00"), due_day=1))
    expense_repo.add(Expense(amount=Decimal("100.00"), spent_date=today.isoformat(), category="Groceries"))
    view = SalaryView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def test_defaults_to_current_month_only(view):
    assert view._table.rowCount() == 2
    assert view._current_key == (date.today().year, date.today().month)


def test_month_keys_span_from_earliest_record_to_now(view):
    keys = view.month_keys()
    assert (2025, 1) in keys
    assert (date.today().year, date.today().month) in keys


def test_selecting_all_shows_full_history(view):
    view.select_all()
    assert view._table.rowCount() == 3


def test_current_month_shows_correct_extra_spending_money(view):
    # Current-month income (2000 + 300) - Rent (900) - Groceries (100) = 1300.
    assert view._lbl_income.text() == f"{date.today().strftime('%B %Y')} Income\n$2,300.00"
    assert view._lbl_bills.text() == "Monthly Bills\n−$900.00"
    assert view._lbl_expenses.text() == f"{date.today().strftime('%B %Y')} Expenses\n−$100.00"
    assert view._lbl_extra.text() == "Extra Spending Money\n$1,300.00"


def test_all_time_view_does_not_produce_bogus_extra_spending_money(view):
    """Regression test for the "All" bills bug.

    Before the fix, `total_bills` was always one month's worth (900) no
    matter the filter, so selecting "All" here would have subtracted 900
    from all-time income (3800) and all-time expenses (100), yielding a
    meaningless "$2,800.00" Extra Spending Money figure. The correct
    behavior is to mark the bills-derived stats N/A for "All" instead of
    reporting a number that mixes a monthly rate with an all-time total.
    """
    view.select_all()

    assert view._lbl_bills.text() == "Monthly Bills\nN/A"
    assert view._lbl_extra.text() == "Extra Spending Money\nN/A"
    # Sanity: the old buggy figure must not appear anywhere.
    assert "2,800.00" not in view._lbl_extra.text()

    assert view._lbl_income.text() == "All-Time Income\n$3,800.00"
    assert view._lbl_expenses.text() == "All-Time Expenses\n−$100.00"

    # The savings visualizer has nothing valid to show either.
    assert view._spend_seg.isHidden()
    assert "specific month" in view._savings_detail.text()


def test_switching_back_from_all_to_a_month_recomputes_extra(view):
    view.select_all()
    view.select_month(date.today().year, date.today().month)

    assert view._lbl_bills.text() == "Monthly Bills\n−$900.00"
    assert view._lbl_extra.text() == "Extra Spending Money\n$1,300.00"
    assert not view._spend_seg.isHidden()
