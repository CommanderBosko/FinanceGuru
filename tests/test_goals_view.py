"""Behavioral tests for the Goals tab's month filter.

Unlike Bills (recurring templates gated by due-day/month), a Goal is filtered
by its own start_date plus a funded/unfunded balance check against payments
made against its mirrored bill — see `_visible_in_month` in goals_view.py.
The view reads date.today(), so a fixed date is patched into the goals_view
module to keep assertions deterministic, matching test_bills_view.py's pattern.
"""

from datetime import date
from decimal import Decimal

import pytest
from PySide6.QtWidgets import QMessageBox

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.note import Note
from financeguru.models.payment import Payment
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
from financeguru.repositories import payments as payment_repo
from financeguru.views.goals_view import GoalsView


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    import financeguru.views.goals_view as goals_view

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 15)

    monkeypatch.setattr(goals_view, "date", _FixedDate)


@pytest.fixture
def view(qapp, temp_db):
    view = GoalsView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def _names(view) -> set[str]:
    return {view._table.item(r, 0).text() for r in range(view._table.rowCount())}


def _select(view, label: str) -> None:
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    view._month_picker.setCurrentIndex(labels.index(label))


def test_defaults_to_all_and_shows_every_goal(view):
    goal_repo.add(Goal(name="Car", price=Decimal("500"), target_date="2026-12-31",
                        start_date="2026-01-01"))
    goal_repo.add(Goal(name="TV", price=Decimal("300"), target_date="2026-09-30",
                        start_date="2026-06-01"))
    view._refresh()

    assert view._month_picker.currentText() == "All"
    assert {"Car", "TV"} <= _names(view)


def test_goal_disappears_once_funded_but_shows_in_completion_month(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("300"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("300"), target_date="2026-03-31",
                        start_date="2026-01-01", bill_id=bill_id))
    # No bill of its own — pulls "February 2026" into the picker so it can be
    # selected below; being bill_id-less it's always visible once started.
    goal_repo.add(Goal(name="Anchor", price=Decimal("50"), target_date="2027-01-01",
                        start_date="2026-02-01"))
    # Fully funds the goal exactly at the start of January — balance-before
    # January was still 300 (>0), so January is the "completion month".
    payment_repo.add(Payment(amount=Decimal("300"), paid_date="2026-01-01", bill_id=bill_id))
    view._refresh()

    _select(view, "January 2026")
    assert "Laptop" in _names(view)

    _select(view, "February 2026")
    assert "Laptop" not in _names(view)

    _select(view, "All")
    assert "Laptop" in _names(view)


def test_goal_hidden_before_its_start_month(view):
    # Pulls "January 2026" into the picker.
    goal_repo.add(Goal(name="Anchor", price=Decimal("50"), target_date="2027-01-01",
                        start_date="2026-01-01"))
    goal_repo.add(Goal(name="Future Goal", price=Decimal("200"), target_date="2026-12-31",
                        start_date="2026-06-01"))
    view._refresh()

    _select(view, "January 2026")
    assert "Future Goal" not in _names(view)

    _select(view, "June 2026")
    assert "Future Goal" in _names(view)


def test_select_month_selects_populated_month_and_falls_back_to_all(view):
    goal_repo.add(Goal(name="Vacation", price=Decimal("400"), target_date="2026-12-31",
                        start_date="2026-08-01"))
    view._refresh()

    view.select_month(2026, 8)
    assert view._month_picker.currentText() == "August 2026"
    assert "Vacation" in _names(view)

    view.select_month(2099, 1)
    assert view._month_picker.currentText() == "All"
    assert "Vacation" in _names(view)


def _left(view, name: str) -> str:
    for r in range(view._table.rowCount()):
        if view._table.item(r, 0).text() == name:
            return view._table.item(r, 2).text()
    raise AssertionError(f"{name!r} not found in table")


def test_amount_left_reflects_balance_as_of_the_selected_month_not_today(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("300"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("300"), target_date="2026-03-31",
                        start_date="2026-01-01", bill_id=bill_id))
    # Fully funds the goal in June — long after January, where it must still
    # show the pre-payment $300.00 balance, not today's fully-paid $0.00.
    payment_repo.add(Payment(amount=Decimal("300"), paid_date="2026-06-01", bill_id=bill_id))
    view._refresh()

    _select(view, "January 2026")
    assert _left(view, "Laptop") == "$300.00"

    _select(view, "All")
    assert _left(view, "Laptop") == "$0.00"


def _delete_selected(view, monkeypatch, answer) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: answer)
    view._table.selectRow(0)
    view._on_delete()


def test_delete_goal_with_linked_notes_yes_deletes_both(view, monkeypatch):
    goal_id = goal_repo.add(Goal(name="Vacation", price=Decimal("400"),
                                  target_date="2026-12-31", start_date="2026-01-01"))
    note_repo.add(Note(body="About vacation", month_year="2026-06", goal_id=goal_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Yes)

    assert goal_repo.get_all() == []
    assert note_repo.get_by_goal_id(goal_id) == []


def test_delete_goal_with_linked_notes_no_keeps_notes_and_clears_link(view, monkeypatch):
    goal_id = goal_repo.add(Goal(name="Vacation", price=Decimal("400"),
                                  target_date="2026-12-31", start_date="2026-01-01"))
    note_id = note_repo.add(Note(body="About vacation", month_year="2026-06", goal_id=goal_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.No)

    assert goal_repo.get_all() == []
    remaining = note_repo.get_for_month(2026, 6)
    assert [n.id for n in remaining] == [note_id]
    assert remaining[0].goal_id is None


def test_delete_goal_with_linked_notes_cancel_deletes_nothing(view, monkeypatch):
    goal_id = goal_repo.add(Goal(name="Vacation", price=Decimal("400"),
                                  target_date="2026-12-31", start_date="2026-01-01"))
    note_repo.add(Note(body="About vacation", month_year="2026-06", goal_id=goal_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Cancel)

    assert len(goal_repo.get_all()) == 1
    assert len(note_repo.get_by_goal_id(goal_id)) == 1
