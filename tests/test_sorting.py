"""Regression tests for click-to-sort column headers.

Two risk classes this guards against:

1. Text-sort bugs — money/date/numeric columns are stored as formatted
   display strings, so without an attached sort_key they'd sort
   alphabetically: "$9.00" after "$100.00", "Month 10" before "Month 9",
   confidence stars in the wrong order (Unicode code points put more stars
   *lower* than fewer). SortableItem (financeguru.views._table) fixes this.

2. Row-identity bugs — every view used to resolve "the selected row" via
   currentRow() indexed straight into a parallel Python list
   (self._bills[row], self._expenses[row], ...). That desyncs the moment a
   table is sorted, so edit/delete/mark-paid could silently act on the wrong
   record. Selection now reads the row's own object back off Qt.UserRole
   data attached to column 0, which stays correct under any sort order.
"""

from datetime import date
from decimal import Decimal

import pytest
from PySide6.QtCore import Qt

from financeguru.models.bill import Bill
from financeguru.models.debt import Debt
from financeguru.models.expense import Expense
from financeguru.models.goal import Goal
from financeguru.models.income import Income
from financeguru.models.payment import Payment
from financeguru.models.stock import Stock
from financeguru.models.stock_tip import StockTip
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import debts as debt_repo
from financeguru.repositories import expenses as expense_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import incomes as income_repo
from financeguru.repositories import payments as payment_repo
from financeguru.repositories import stock_tips as tip_repo
from financeguru.repositories import stocks as stock_repo
from financeguru.views.bills_view import BillsView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.debt_snowball_view import DebtSnowballView
from financeguru.views.expenses_view import ExpensesView
from financeguru.views.goals_view import GoalsView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.salary_view import SalaryView
from financeguru.views.stock_tips_view import StockTipsView
from financeguru.views.stocks_view import StocksView


def _dispose(widget, qapp) -> None:
    widget.deleteLater()
    qapp.processEvents()


def _sort(table, col, ascending=True):
    order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder
    table.sortByColumn(col, order)


def _col_texts(table, col):
    return [table.item(r, col).text() for r in range(table.rowCount())]


# ── Bills ──────────────────────────────────────────────────────────────────

def test_bills_starts_unsorted(qapp, temp_db):
    # No click yet -> natural repository order, not a forced default sort.
    bill_repo.add(Bill(name="Zebra", amount=Decimal("10"), due_day=1, recurrence="monthly"))
    view = BillsView()
    assert view._table.horizontalHeader().sortIndicatorSection() == -1
    _dispose(view, qapp)


def test_bills_due_day_sorts_numerically_not_as_text(qapp, temp_db):
    bill_repo.add(Bill(name="A", amount=Decimal("10"), due_day=20, recurrence="monthly"))
    bill_repo.add(Bill(name="B", amount=Decimal("10"), due_day=5, recurrence="monthly"))
    bill_repo.add(Bill(name="C", amount=Decimal("10"), due_day=9, recurrence="monthly"))
    view = BillsView()
    _sort(view._table, 2)  # Due Day
    assert _col_texts(view._table, 2) == ["5", "9", "20"]
    _sort(view._table, 2, ascending=False)
    assert _col_texts(view._table, 2) == ["20", "9", "5"]
    _dispose(view, qapp)


def test_bills_amount_sorts_numerically(qapp, temp_db):
    bill_repo.add(Bill(name="Big", amount=Decimal("1000.00"), due_day=1, recurrence="monthly"))
    bill_repo.add(Bill(name="Small", amount=Decimal("50.00"), due_day=1, recurrence="monthly"))
    view = BillsView()
    _sort(view._table, 1)  # Amount
    assert _col_texts(view._table, 0) == ["Small", "Big"]
    _dispose(view, qapp)


def test_bills_edit_targets_correct_row_after_sort(qapp, temp_db):
    bill_repo.add(Bill(name="Zebra", amount=Decimal("10"), due_day=1, recurrence="monthly"))
    bill_repo.add(Bill(name="Apple", amount=Decimal("20"), due_day=2, recurrence="monthly"))
    view = BillsView()
    _sort(view._table, 0)  # Name -> Apple, Zebra
    assert _col_texts(view._table, 0) == ["Apple", "Zebra"]
    view._table.selectRow(0)
    assert view._selected_bill().name == "Apple"
    _dispose(view, qapp)


# ── Payments ───────────────────────────────────────────────────────────────

def test_payments_amount_sorts_numerically_and_delete_targets_correct_row(qapp, temp_db):
    today = date.today().isoformat()
    payment_repo.add(Payment(amount=Decimal("900.00"), paid_date=today, notes="big"))
    payment_repo.add(Payment(amount=Decimal("40.00"), paid_date=today, notes="small"))
    view = PaymentsView()
    _sort(view._table, 1)  # Amount
    assert _col_texts(view._table, 3) == ["small", "big"]
    view._table.selectRow(0)
    rec = view._selected_row()
    assert rec["notes"] == "small"
    _dispose(view, qapp)


# ── Expenses ───────────────────────────────────────────────────────────────

def test_expenses_amount_sorts_numerically_and_edit_targets_correct_row(qapp, temp_db):
    today = date.today().isoformat()
    expense_repo.add(Expense(amount=Decimal("500.00"), spent_date=today, category="Rent", notes="big"))
    expense_repo.add(Expense(amount=Decimal("15.00"), spent_date=today, category="Coffee", notes="small"))
    view = ExpensesView()
    _sort(view._table, 0)  # Amount is column 0 here
    assert _col_texts(view._table, 3) == ["small", "big"]
    view._table.selectRow(0)
    assert view._selected_expense().notes == "small"
    _dispose(view, qapp)


# ── Income (Salary tab) ────────────────────────────────────────────────────

def test_income_amount_sorts_numerically_and_edit_targets_correct_row(qapp, temp_db):
    income_repo.add(Income(name="Big Job", amount=Decimal("5000.00"), frequency="monthly"))
    income_repo.add(Income(name="Side Gig", amount=Decimal("300.00"), frequency="monthly"))
    view = SalaryView()
    _sort(view._table, 1)  # Amount
    assert _col_texts(view._table, 0) == ["Side Gig", "Big Job"]
    view._table.selectRow(0)
    assert view._selected().name == "Side Gig"
    _dispose(view, qapp)


# ── Stocks ─────────────────────────────────────────────────────────────────

def test_stocks_shares_sorts_numerically_despite_comma_separators(qapp, temp_db):
    stock_repo.add(Stock(ticker="AAA", shares=Decimal("1000"), purchase_price=Decimal("10.00"), purchase_date="2026-01-01"))
    stock_repo.add(Stock(ticker="BBB", shares=Decimal("50"), purchase_price=Decimal("10.00"), purchase_date="2026-01-01"))
    view = StocksView()
    _sort(view._table, 1)  # Shares
    assert _col_texts(view._table, 0) == ["BBB", "AAA"]
    view._table.selectRow(0)
    assert view._selected_stock().ticker == "BBB"
    _dispose(view, qapp)


# ── Stock Tips ─────────────────────────────────────────────────────────────

def test_stock_tips_confidence_stars_sort_numerically(qapp, temp_db):
    # Unicode-code-point trap: "★" < "☆", so more-filled star strings sort
    # *lower* than fewer as plain text — confidence must sort by the int.
    tip_repo.add(StockTip(id=0, ticker="LOW", action="buy", target_price=Decimal("10"),
                           confidence=1, notes=None, added_date="2026-01-01"))
    tip_repo.add(StockTip(id=0, ticker="HIGH", action="buy", target_price=Decimal("10"),
                           confidence=5, notes=None, added_date="2026-01-01"))
    view = StockTipsView()
    _sort(view._table, 3)  # Confidence
    assert _col_texts(view._table, 0) == ["LOW", "HIGH"]
    view._table.selectRow(0)
    assert view._selected_tip().ticker == "LOW"
    _dispose(view, qapp)


# ── Goals ──────────────────────────────────────────────────────────────────

def test_goals_months_left_sorts_numerically_and_edit_targets_correct_row(qapp, temp_db):
    today = date.today()
    goal_repo.add(Goal(name="Soon", price=Decimal("100"),
                        target_date=date(today.year, today.month, 28).isoformat()))
    far_year = today.year + 2
    goal_repo.add(Goal(name="Far", price=Decimal("100"),
                        target_date=date(far_year, today.month, 28).isoformat()))
    view = GoalsView()
    _sort(view._table, 4)  # Months Left
    assert _col_texts(view._table, 0) == ["Soon", "Far"]
    view._table.selectRow(0)
    assert view._selected_goal().name == "Soon"
    _dispose(view, qapp)


# ── Debt Snowball ──────────────────────────────────────────────────────────

def test_debt_balance_sorts_numerically_and_edit_targets_correct_row(qapp, temp_db):
    debt_repo.add(Debt(id=0, name="Big Loan", balance=Decimal("9000.00"),
                        interest_rate=Decimal("5.00"), minimum_payment=Decimal("50.00"), notes=None))
    debt_repo.add(Debt(id=0, name="Small Card", balance=Decimal("300.00"),
                        interest_rate=Decimal("20.00"), minimum_payment=Decimal("25.00"), notes=None))
    view = DebtSnowballView()
    _sort(view._debt_table, 1)  # Balance
    assert _col_texts(view._debt_table, 0) == ["Small Card", "Big Loan"]
    view._debt_table.selectRow(0)
    assert view._selected_debt().name == "Small Card"
    _dispose(view, qapp)


def test_debt_lump_table_month_sorts_numerically_and_remove_targets_correct_entry(qapp, temp_db):
    view = DebtSnowballView()
    view._lump_sums = [(12, 500.0), (3, 100.0), (7, 250.0)]
    view._render_lump_table()
    _sort(view._lump_table, 0)  # Month -> would be "Month 12","Month 3","Month 7" as text
    assert _col_texts(view._lump_table, 0) == ["Month 3", "Month 7", "Month 12"]

    view._lump_table.selectRow(0)  # "Month 3" after sorting
    view._on_remove_lump()
    assert (3, 100.0) not in view._lump_sums
    assert (12, 500.0) in view._lump_sums
    assert (7, 250.0) in view._lump_sums
    assert len(view._lump_sums) == 2
    _dispose(view, qapp)


# ── Dashboard (display-only, no selection/edit path) ────────────────────────

def test_dashboard_amount_and_due_day_sort_numerically(qapp, temp_db):
    today = date.today()
    bill_repo.add(Bill(name="Twenty", amount=Decimal("1000.00"), due_day=20, recurrence="monthly"))
    bill_repo.add(Bill(name="Five", amount=Decimal("50.00"), due_day=5, recurrence="monthly"))
    bill_repo.add(Bill(name="Nine", amount=Decimal("75.00"), due_day=9, recurrence="monthly"))
    view = DashboardView()
    _sort(view._bills_table, 2)  # Due Day
    assert _col_texts(view._bills_table, 2) == ["5", "9", "20"]
    _sort(view._bills_table, 1)  # Amount
    assert _col_texts(view._bills_table, 0) == ["Five", "Nine", "Twenty"]
    _dispose(view, qapp)
