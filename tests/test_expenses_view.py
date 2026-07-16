"""Behavioral tests for the Expenses tab's month filter and live search.

The construction/refresh contract is covered by test_views_smoke; these tests
drive the two filters (mirroring the Payments tab) against a seeded table and
assert on the visible row set.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.expense import Expense
from financeguru.repositories import expenses as expense_repo
from financeguru.views.expenses_view import ExpensesView


@pytest.fixture
def view(qapp, temp_db):
    today = date.today()
    expense_repo.add(Expense(amount=Decimal("42.75"), spent_date=today.isoformat(),
                             category="Groceries", notes="weekly shop"))
    expense_repo.add(Expense(amount=Decimal("12.00"), spent_date=today.isoformat(),
                             category="Restaurants", notes=None))
    expense_repo.add(Expense(amount=Decimal("99.99"), spent_date="2025-01-15",
                             category="Entertainment", notes="old concert"))
    view = ExpensesView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def test_defaults_to_current_month_only(view):
    assert view._table.rowCount() == 2
    assert view._chk_current_only.isChecked()


def test_unchecking_month_filter_shows_full_history(view):
    view._chk_current_only.setChecked(False)
    assert view._table.rowCount() == 3


def test_search_filters_across_display_fields(view):
    view._chk_current_only.setChecked(False)

    view._search.setText("concert")          # notes
    assert view._table.rowCount() == 1
    assert view._table.item(0, 3).text() == "old concert"

    view._search.setText("groceries")        # category, case-insensitive
    assert view._table.rowCount() == 1

    view._search.setText("$12.00")           # displayed amount
    assert view._table.rowCount() == 1

    view._search.setText("no such thing")
    assert view._table.rowCount() == 0

    view._search.clear()
    assert view._table.rowCount() == 3


def test_search_chains_with_month_filter(view):
    # "concert" is on last year's expense; with the month filter on it must
    # stay hidden even though search alone would match it.
    view._search.setText("concert")
    assert view._table.rowCount() == 0
