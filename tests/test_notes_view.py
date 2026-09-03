"""Behavioral tests for the Notes tab: its month picker (no "All", earliest-
note-backward, like Payments/Expenses but without the unfiltered view),
newest-first ordering, filing under the *selected* month, and the link
indicator's cross-tab navigation signal.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.note import Note
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
from financeguru.views.notes_view import NotesView, _bill_target_month


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    import financeguru.views.notes_view as notes_view
    import financeguru.views._month_filter as month_filter

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 6, 15)

    # NotesView delegates its month-picker's "current month" to the shared
    # _month_filter helper (unlike Bills/Goals, which compute it inline), so
    # both modules' `date` need patching for a deterministic "today".
    monkeypatch.setattr(notes_view, "date", _FixedDate)
    monkeypatch.setattr(month_filter, "date", _FixedDate)


@pytest.fixture
def view(qapp, temp_db):
    view = NotesView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def _select(view, label: str) -> None:
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    view._month_picker.setCurrentIndex(labels.index(label))


def _bodies(view) -> list[str]:
    return [view._table.item(r, 1).toolTip() for r in range(view._table.rowCount())]


def test_defaults_to_current_month_with_no_all_entry(view):
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    assert "All" not in labels
    assert view._month_picker.currentText() == "June 2026"


def test_only_current_month_when_there_are_no_notes_yet(view):
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    assert labels == ["June 2026"]


def test_month_picker_grows_backward_to_earliest_note(view):
    note_repo.add(Note(body="Old", month_year="2026-03"))
    view._refresh()
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    assert labels == ["June 2026", "May 2026", "April 2026", "March 2026"]


def test_notes_for_selected_month_sorted_newest_first(view):
    note_repo.add(Note(body="Earlier", month_year="2026-06", created_at="2026-06-01T09:00:00"))
    note_repo.add(Note(body="Later", month_year="2026-06", created_at="2026-06-10T09:00:00"))
    view._refresh()
    assert _bodies(view) == ["Later", "Earlier"]


def test_a_note_from_another_month_is_not_shown(view):
    note_repo.add(Note(body="March note", month_year="2026-03"))
    view._refresh()
    assert _bodies(view) == []
    _select(view, "March 2026")
    assert _bodies(view) == ["March note"]


def test_current_month_year_reflects_the_selected_picker_entry(view):
    # This is what _on_add hands to NoteDialog — a new note is filed under
    # whichever month is selected, not necessarily today's, so backfilling a
    # past month works.
    note_repo.add(Note(body="Old", month_year="2026-03"))
    view._refresh()
    _select(view, "March 2026")
    assert view._current_month_year() == "2026-03"


def test_bill_target_month_for_monthly_bill_is_today():
    bill = Bill(name="Rent", amount=Decimal("1000"), due_day=1, recurrence="monthly")
    assert _bill_target_month(bill, date(2026, 6, 15)) == (2026, 6)


def test_bill_target_month_for_yearly_bill_uses_this_year_if_not_passed():
    bill = Bill(name="Registration", amount=Decimal("200"), due_day=1,
                due_month=9, recurrence="yearly")
    assert _bill_target_month(bill, date(2026, 6, 15)) == (2026, 9)


def test_bill_target_month_for_yearly_bill_rolls_to_next_year_if_passed():
    bill = Bill(name="Registration", amount=Decimal("200"), due_day=1,
                due_month=3, recurrence="yearly")
    assert _bill_target_month(bill, date(2026, 6, 15)) == (2027, 3)


def test_bill_target_month_for_one_time_bill_is_its_own_due_date():
    bill = Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                due_month=3, due_year=2027, recurrence="one-time")
    assert _bill_target_month(bill, date(2026, 6, 15)) == (2027, 3)


def test_bill_link_indicator_emits_navigate_requested_with_bills_target(view):
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1,
                                  recurrence="monthly"))
    note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    received = []
    view.navigate_requested.connect(lambda *args: received.append(args))
    button = view._table.cellWidget(0, 2)
    assert button is not None
    assert button.text() == "→ Rent"
    button.click()

    assert received == [("bills", 2026, 6)]


def test_goal_link_indicator_emits_navigate_requested_with_goals_target(view):
    goal_id = goal_repo.add(Goal(name="Vacation", price=Decimal("2000"),
                                  target_date="2026-12-31", start_date="2026-08-01"))
    note_repo.add(Note(body="About vacation", month_year="2026-06", goal_id=goal_id))
    view._refresh()

    received = []
    view.navigate_requested.connect(lambda *args: received.append(args))
    button = view._table.cellWidget(0, 2)
    assert button is not None
    assert button.text() == "→ Vacation"
    button.click()

    assert received == [("goals", 2026, 8)]


def test_bill_target_month_clamps_forward_to_a_not_yet_started_goal():
    # A Goal's mirrored bill is always monthly, so _bill_target_month would
    # otherwise return "today" — a month BillsView's own goal-start gating
    # hides this bill in, since the goal hasn't started yet. goal_start must
    # clamp the target forward to where the bill actually becomes visible.
    bill = Bill(name="Vacation", amount=Decimal("100"), due_day=1, recurrence="monthly")
    goal_start = date(2026, 9, 1)  # after the fixed "today" of 2026-06-15
    assert _bill_target_month(bill, date(2026, 6, 15), goal_start) == (2026, 9)


def test_bill_target_month_ignores_a_goal_start_already_in_the_past():
    bill = Bill(name="Vacation", amount=Decimal("100"), due_day=1, recurrence="monthly")
    goal_start = date(2026, 1, 1)  # before "today" — already started, no clamp needed
    assert _bill_target_month(bill, date(2026, 6, 15), goal_start) == (2026, 6)


def test_goal_mirrored_bill_link_navigates_to_the_goals_own_start_month(view):
    bill_id = bill_repo.add(Bill(name="Vacation", amount=Decimal("100"), due_day=1,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Vacation", price=Decimal("1200"), target_date="2027-01-01",
                        start_date="2026-09-01", bill_id=bill_id))
    note_repo.add(Note(body="About the vacation bill", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    received = []
    view.navigate_requested.connect(lambda *args: received.append(args))
    button = view._table.cellWidget(0, 2)
    assert button is not None
    button.click()

    # Not (2026, 6) — that's "today" per fixed_today, but the goal doesn't
    # start until September, so BillsView would show nothing there.
    assert received == [("bills", 2026, 9)]


def test_unlinked_note_has_no_link_widget(view):
    note_repo.add(Note(body="Just a thought", month_year="2026-06"))
    view._refresh()
    assert view._table.cellWidget(0, 2) is None
