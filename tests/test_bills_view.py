"""Behavioral tests for the Bills tab's month filter.

Unlike Payments/Income (dated log entries filtered by string prefix), Bills
are recurring templates filtered via Bill.is_due_in plus a goal-specific gate
on the linked Goal's start_date. The view reads date.today(), so a fixed date
is patched into the bills_view module to keep assertions deterministic.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.views.bills_view import BillsView


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    import financeguru.views.bills_view as bills_view

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 15)

    monkeypatch.setattr(bills_view, "date", _FixedDate)


@pytest.fixture
def view(qapp, temp_db):
    view = BillsView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def _names(view) -> set[str]:
    return {view._table.item(r, 0).text() for r in range(view._table.rowCount())}


def _select(view, label: str) -> None:
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    view._month_picker.setCurrentIndex(labels.index(label))


def test_defaults_to_current_month(view):
    assert view._month_picker.currentText() == "June 2026"


def test_monthly_bill_always_visible(view):
    bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1, recurrence="monthly"))
    # A one-time bill just to pull a December entry into the picker — the
    # month range is only ever as wide as what's "interesting" (see
    # _month_entries), so nothing offers "December 2026" on its own here.
    bill_repo.add(Bill(name="Property Tax", amount=Decimal("50"), due_day=1,
                        due_month=12, due_year=2026, recurrence="one-time"))
    view._refresh()
    for label in ("June 2026", "December 2026", "All"):
        _select(view, label)
        assert "Rent" in _names(view)


def test_yearly_bill_only_visible_in_its_due_month(view):
    bill_repo.add(Bill(name="Car Registration", amount=Decimal("200"), due_day=10,
                        due_month=9, recurrence="yearly"))
    view._refresh()

    _select(view, "June 2026")
    assert "Car Registration" not in _names(view)

    _select(view, "September 2026")
    assert "Car Registration" in _names(view)

    _select(view, "All")
    assert "Car Registration" in _names(view)


def test_one_time_bill_only_visible_in_its_exact_month(view):
    bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                        due_month=3, due_year=2027, recurrence="one-time"))
    view._refresh()

    _select(view, "June 2026")
    assert "New Roof" not in _names(view)

    _select(view, "All")
    assert "New Roof" in _names(view)


def test_goal_bill_hidden_before_start_month_visible_at_and_after(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    _select(view, "June 2026")
    assert "Laptop" not in _names(view)

    _select(view, "August 2026")
    assert "Laptop" in _names(view)

    _select(view, "December 2026")
    assert "Laptop" in _names(view)


def test_goal_bill_always_visible_under_all(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    _select(view, "All")
    assert "Laptop" in _names(view)


def test_inactive_bill_still_gated_by_month(view):
    bill_repo.add(Bill(name="Old Gym", amount=Decimal("30"), due_day=1,
                        due_month=1, due_year=2025, recurrence="one-time", is_active=False))
    view._refresh()

    _select(view, "June 2026")
    assert "Old Gym" not in _names(view)

    _select(view, "All")
    assert "Old Gym" in _names(view)


def test_month_entries_include_goal_and_one_time_months(view):
    bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                        due_month=3, due_year=2027, recurrence="one-time"))
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    labels = {view._month_picker.itemText(i) for i in range(view._month_picker.count())}
    assert "All" in labels
    assert "June 2026" in labels       # today
    assert "March 2027" in labels      # one-time bill's due month
    assert "August 2026" in labels     # goal start_date
    assert "December 2026" in labels   # goal target_date


def test_falls_back_to_current_month_when_selection_vanishes(view):
    # "March 2027" only exists in the picker because of this one-time bill.
    bill_id = bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                                  due_month=3, due_year=2027, recurrence="one-time"))
    view._refresh()
    _select(view, "March 2027")
    assert view._month_picker.currentText() == "March 2027"

    # Deleting it removes "March 2027" from the rebuilt picker entirely —
    # distinct from the empty-currentText "first population" case, this is
    # a previously-selected month disappearing out from under the user.
    bill_repo.delete(bill_id)
    view._refresh()

    assert view._month_picker.currentText() == "June 2026"
