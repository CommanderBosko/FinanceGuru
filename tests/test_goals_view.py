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


def test_defaults_to_all_and_shows_every_goal(view):
    goal_repo.add(Goal(name="Car", price=Decimal("500"), target_date="2026-12-31",
                        start_date="2026-01-01"))
    goal_repo.add(Goal(name="TV", price=Decimal("300"), target_date="2026-09-30",
                        start_date="2026-06-01"))
    view._refresh()

    assert view._current_key is None
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

    view.select_month(2026, 1)
    assert "Laptop" in _names(view)

    view.select_month(2026, 2)
    assert "Laptop" not in _names(view)

    view.select_all()
    assert "Laptop" in _names(view)


def test_goal_hidden_before_its_start_month(view):
    # Pulls (2026, 1) into month_keys().
    goal_repo.add(Goal(name="Anchor", price=Decimal("50"), target_date="2027-01-01",
                        start_date="2026-01-01"))
    goal_repo.add(Goal(name="Future Goal", price=Decimal("200"), target_date="2026-12-31",
                        start_date="2026-06-01"))
    view._refresh()

    view.select_month(2026, 1)
    assert "Future Goal" not in _names(view)

    view.select_month(2026, 6)
    assert "Future Goal" in _names(view)


def test_select_month_selects_populated_month_and_falls_back_to_all(view):
    goal_repo.add(Goal(name="Vacation", price=Decimal("400"), target_date="2026-12-31",
                        start_date="2026-08-01"))
    view._refresh()

    view.select_month(2026, 8)
    assert view._current_key == (2026, 8)
    assert "Vacation" in _names(view)

    # 2099-01 isn't one of this tab's own populated entries (see
    # month_keys) — falls back to "All" so a Notes-tab link click is never
    # left on a dead selection.
    view.select_month(2099, 1)
    assert view._current_key is None
    assert "Vacation" in _names(view)


def test_select_month_strict_skips_the_fallback(view):
    # MainWindow's global broadcast passes strict=True specifically so the
    # toolbar can never show a specific month while this tab silently shows
    # every goal instead — see main_window.py's _STRICT_ON_GLOBAL.
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("300"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("300"), target_date="2026-03-31",
                        start_date="2026-01-01", bill_id=bill_id))
    payment_repo.add(Payment(amount=Decimal("300"), paid_date="2026-02-01", bill_id=bill_id))
    view._refresh()

    # Fully funded well before 2099 and not one of this tab's own populated
    # entries — non-strict select_month would fall back to "All" (which
    # shows it anyway, ignoring the funded cutoff). Strict mode selects
    # 2099-01 literally: the goal is long since funded, so it's correctly
    # absent rather than appearing via a silent All fallback.
    view.select_month(2099, 1, strict=True)
    assert view._current_key == (2099, 1)
    assert "Laptop" not in _names(view)


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

    view.select_month(2026, 1)
    assert _left(view, "Laptop") == "$300.00"

    view.select_all()
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


def test_delete_goal_counts_and_deletes_notes_linked_via_its_mirrored_bill(view, monkeypatch):
    # A note can link to a Goal's own auto-generated bill (via NoteDialog's
    # "Bill" link type) instead of the Goal itself — that note must count
    # toward, and be swept up by, the same delete-cascade prompt, since the
    # bill disappears in the same action as the goal.
    bill_id = bill_repo.add(Bill(name="Vacation", amount=Decimal("100"), due_day=1,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Vacation", price=Decimal("400"),
                        target_date="2026-12-31", start_date="2026-01-01", bill_id=bill_id))
    note_repo.add(Note(body="About the vacation bill", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Yes)

    assert goal_repo.get_all() == []
    assert note_repo.get_by_bill_id(bill_id) == []


def test_delete_goal_no_clears_bill_linked_notes_instead_of_leaving_them_dangling(view, monkeypatch):
    bill_id = bill_repo.add(Bill(name="Vacation", amount=Decimal("100"), due_day=1,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Vacation", price=Decimal("400"),
                        target_date="2026-12-31", start_date="2026-01-01", bill_id=bill_id))
    note_id = note_repo.add(Note(body="About the vacation bill", month_year="2026-06",
                                  bill_id=bill_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.No)

    assert goal_repo.get_all() == []
    remaining = note_repo.get_for_month(2026, 6)
    assert [n.id for n in remaining] == [note_id]
    assert remaining[0].bill_id is None
