"""Behavioral tests for the Bills tab's month filter.

Unlike Payments/Income (dated log entries filtered by string prefix), Bills
are recurring templates filtered via Bill.is_due_in plus a goal-specific gate
on the linked Goal's start_date. The view reads date.today(), so a fixed date
is patched into the bills_view module to keep assertions deterministic.

BillsView no longer owns a month-picker widget — the global month selector in
MainWindow now owns the combo (see test_main_window_global_month.py) and
drives every affected tab through select_month()/select_all(). These tests
exercise BillsView's own state (_current_key, month_keys()) and filtering
rule directly, standalone, exactly as MainWindow would drive it.
"""

from datetime import date
from decimal import Decimal

import pytest
from PySide6.QtWidgets import QMessageBox

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.note import Note
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
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


def test_defaults_to_current_month(view):
    assert view._current_key == (2026, 6)


def test_monthly_bill_always_visible(view):
    bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1, recurrence="monthly"))
    # A one-time bill just to pull a December key into month_keys() — the
    # month range is only ever as wide as what's "interesting" (see
    # _month_entries), so nothing offers (2026, 12) on its own here.
    bill_repo.add(Bill(name="Property Tax", amount=Decimal("50"), due_day=1,
                        due_month=12, due_year=2026, recurrence="one-time"))
    view._refresh()
    for year, month in ((2026, 6), (2026, 12)):
        view.select_month(year, month)
        assert "Rent" in _names(view)
    view.select_all()
    assert "Rent" in _names(view)


def test_yearly_bill_only_visible_in_its_due_month(view):
    bill_repo.add(Bill(name="Car Registration", amount=Decimal("200"), due_day=10,
                        due_month=9, recurrence="yearly"))
    view._refresh()

    view.select_month(2026, 6)
    assert "Car Registration" not in _names(view)

    view.select_month(2026, 9)
    assert "Car Registration" in _names(view)

    view.select_all()
    assert "Car Registration" in _names(view)


def test_one_time_bill_only_visible_in_its_exact_month(view):
    bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                        due_month=3, due_year=2027, recurrence="one-time"))
    view._refresh()

    view.select_month(2026, 6)
    assert "New Roof" not in _names(view)

    view.select_all()
    assert "New Roof" in _names(view)


def test_goal_bill_hidden_before_start_month_visible_at_and_after(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    view.select_month(2026, 6)
    assert "Laptop" not in _names(view)

    view.select_month(2026, 8)
    assert "Laptop" in _names(view)

    view.select_month(2026, 12)
    assert "Laptop" in _names(view)


def test_goal_bill_always_visible_under_all(view):
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    view.select_all()
    assert "Laptop" in _names(view)


def test_inactive_bill_still_gated_by_month(view):
    bill_repo.add(Bill(name="Old Gym", amount=Decimal("30"), due_day=1,
                        due_month=1, due_year=2025, recurrence="one-time", is_active=False))
    view._refresh()

    view.select_month(2026, 6)
    assert "Old Gym" not in _names(view)

    view.select_all()
    assert "Old Gym" in _names(view)


def test_month_keys_include_goal_and_one_time_months(view):
    bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                        due_month=3, due_year=2027, recurrence="one-time"))
    bill_id = bill_repo.add(Bill(name="Laptop", amount=Decimal("200"), due_day=15,
                                  recurrence="monthly"))
    goal_repo.add(Goal(name="Laptop", price=Decimal("1200"), target_date="2026-12-31",
                        start_date="2026-08-01", bill_id=bill_id))
    view._refresh()

    keys = set(view.month_keys())
    assert (2026, 6) in keys    # today
    assert (2027, 3) in keys   # one-time bill's due month
    assert (2026, 8) in keys   # goal start_date
    assert (2026, 12) in keys  # goal target_date


def test_select_month_selects_populated_month_and_falls_back_to_all(view):
    bill_repo.add(Bill(name="Car Registration", amount=Decimal("200"), due_day=10,
                        due_month=9, recurrence="yearly"))
    view._refresh()

    view.select_month(2026, 9)
    assert view._current_key == (2026, 9)
    assert "Car Registration" in _names(view)

    # 2099-01 isn't one of this tab's own populated entries (see
    # month_keys) — falls back to "All" so a Notes-tab link click is never
    # left on a dead selection.
    view.select_month(2099, 1)
    assert view._current_key is None
    assert "Car Registration" in _names(view)


def test_select_month_strict_skips_the_fallback(view):
    # MainWindow's global broadcast passes strict=True specifically so the
    # toolbar can never show a specific month while this tab silently shows
    # "All" instead — see main_window.py's _STRICT_ON_GLOBAL. 2099-01 isn't
    # one of this tab's own populated entries, but strict mode selects it
    # literally anyway, rendering an empty table (nothing due in January)
    # rather than falling back to "All" (which would show Car Registration).
    bill_repo.add(Bill(name="Car Registration", amount=Decimal("200"), due_day=10,
                        due_month=9, recurrence="yearly"))
    view._refresh()

    view.select_month(2099, 1, strict=True)
    assert view._current_key == (2099, 1)
    assert _names(view) == set()


def _delete_selected(view, monkeypatch, answer) -> None:
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: answer)
    view._table.selectRow(0)
    view._on_delete()


def test_delete_with_no_linked_notes_is_unchanged(view, monkeypatch):
    bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Yes)
    assert bill_repo.get_all() == []


def test_delete_bill_with_linked_notes_yes_deletes_both(view, monkeypatch):
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1))
    note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Yes)

    assert bill_repo.get_all() == []
    assert note_repo.get_by_bill_id(bill_id) == []


def test_delete_bill_with_linked_notes_no_keeps_notes_and_clears_link(view, monkeypatch):
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1))
    note_id = note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.No)

    assert bill_repo.get_all() == []
    remaining = note_repo.get_for_month(2026, 6)
    assert [n.id for n in remaining] == [note_id]
    assert remaining[0].bill_id is None


def test_delete_bill_with_linked_notes_cancel_deletes_nothing(view, monkeypatch):
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1))
    note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    view._refresh()

    _delete_selected(view, monkeypatch, QMessageBox.StandardButton.Cancel)

    assert len(bill_repo.get_all()) == 1
    assert len(note_repo.get_by_bill_id(bill_id)) == 1


def test_current_key_persists_across_refresh_even_if_now_empty(view):
    # Unlike the old local-combo design (which auto-fell-back to the current
    # month once a previously selected month vanished from the rebuilt
    # picker), BillsView no longer owns a combo to fall back via — that
    # "previous selection vanished" auto-correction now lives one layer up,
    # in MainWindow's global list (see test_month_filter.py's
    # populate_from_keys tests). Once _current_key is set, _refresh() just
    # re-filters against it as-is, showing an empty table rather than
    # silently jumping elsewhere — matching every other affected tab's new
    # "empty state for a month with nothing relevant" behavior.
    bill_id = bill_repo.add(Bill(name="New Roof", amount=Decimal("5000"), due_day=1,
                                  due_month=3, due_year=2027, recurrence="one-time"))
    view._refresh()
    view.select_month(2027, 3)
    assert "New Roof" in _names(view)

    bill_repo.delete(bill_id)
    view._refresh()

    assert view._current_key == (2027, 3)
    assert _names(view) == set()
