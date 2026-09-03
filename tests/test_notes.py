from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.note import Note
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo


def test_add_returns_id_and_round_trips():
    new_id = note_repo.add(Note(body="Remember to check the water bill", month_year="2026-06"))
    assert new_id

    notes = note_repo.get_for_month(2026, 6)
    assert len(notes) == 1
    note = notes[0]
    assert note.id == new_id
    assert note.body == "Remember to check the water bill"
    assert note.month_year == "2026-06"
    assert note.bill_id is None
    assert note.goal_id is None
    assert note.created_at  # auto-set, non-empty


def test_get_for_month_filters_by_month_and_ignores_others():
    note_repo.add(Note(body="June note", month_year="2026-06"))
    note_repo.add(Note(body="July note", month_year="2026-07"))
    assert [n.body for n in note_repo.get_for_month(2026, 6)] == ["June note"]
    assert [n.body for n in note_repo.get_for_month(2026, 7)] == ["July note"]
    assert note_repo.get_for_month(2026, 8) == []


def test_get_for_month_orders_newest_first():
    note_repo.add(Note(body="First", month_year="2026-06", created_at="2026-06-01T10:00:00"))
    note_repo.add(Note(body="Second", month_year="2026-06", created_at="2026-06-15T10:00:00"))
    note_repo.add(Note(body="Third", month_year="2026-06", created_at="2026-06-10T10:00:00"))
    bodies = [n.body for n in note_repo.get_for_month(2026, 6)]
    assert bodies == ["Second", "Third", "First"]


def test_get_for_month_breaks_same_timestamp_tie_by_id_desc():
    same = "2026-06-01T10:00:00"
    first_id = note_repo.add(Note(body="First", month_year="2026-06", created_at=same))
    second_id = note_repo.add(Note(body="Second", month_year="2026-06", created_at=same))
    ids = [n.id for n in note_repo.get_for_month(2026, 6)]
    assert ids == [second_id, first_id]


def test_earliest_month_none_when_no_notes():
    assert note_repo.earliest_month() is None


def test_earliest_month_returns_the_oldest_month_year():
    note_repo.add(Note(body="a", month_year="2026-06"))
    note_repo.add(Note(body="b", month_year="2025-01"))
    note_repo.add(Note(body="c", month_year="2026-03"))
    assert note_repo.earliest_month() == "2025-01"


def test_update_changes_body_and_link():
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1200.00"), due_day=1))
    note_id = note_repo.add(Note(body="Original", month_year="2026-06"))
    note_repo.update(Note(id=note_id, body="Edited", month_year="2026-06", bill_id=bill_id))

    note = note_repo.get_for_month(2026, 6)[0]
    assert note.body == "Edited"
    assert note.bill_id == bill_id


def test_delete_removes_the_note():
    note_id = note_repo.add(Note(body="Temporary", month_year="2026-06"))
    note_repo.delete(note_id)
    assert note_repo.get_for_month(2026, 6) == []


def test_get_by_bill_id_and_goal_id():
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1200.00"), due_day=1))
    goal_id = goal_repo.add(Goal(name="Car", price=Decimal("500"), target_date="2026-12-31"))
    bill_note = note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    goal_note = note_repo.add(Note(body="About car", month_year="2026-06", goal_id=goal_id))
    note_repo.add(Note(body="Unlinked", month_year="2026-06"))

    assert [n.id for n in note_repo.get_by_bill_id(bill_id)] == [bill_note]
    assert [n.id for n in note_repo.get_by_goal_id(goal_id)] == [goal_note]


def test_delete_for_bill_and_delete_for_goal_remove_only_linked_notes():
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1200.00"), due_day=1))
    goal_id = goal_repo.add(Goal(name="Car", price=Decimal("500"), target_date="2026-12-31"))
    note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))
    note_repo.add(Note(body="About car", month_year="2026-06", goal_id=goal_id))
    unlinked_id = note_repo.add(Note(body="Unlinked", month_year="2026-06"))

    note_repo.delete_for_bill(bill_id)
    note_repo.delete_for_goal(goal_id)

    remaining = note_repo.get_for_month(2026, 6)
    assert [n.id for n in remaining] == [unlinked_id]


def test_deleting_linked_bill_clears_the_link_but_keeps_the_note():
    # The notes.bill_id FK is declared ON DELETE SET NULL — deleting the bill
    # directly (bypassing the view's own "delete the notes too?" prompt)
    # should clear the link rather than leave it dangling or cascade-delete
    # the note.
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1200.00"), due_day=1))
    note_id = note_repo.add(Note(body="About rent", month_year="2026-06", bill_id=bill_id))

    bill_repo.delete(bill_id)

    note = note_repo.get_for_month(2026, 6)[0]
    assert note.id == note_id
    assert note.bill_id is None


def test_deleting_linked_goal_clears_the_link_but_keeps_the_note():
    goal_id = goal_repo.add(Goal(name="Car", price=Decimal("500"), target_date="2026-12-31"))
    note_id = note_repo.add(Note(body="About car", month_year="2026-06", goal_id=goal_id))

    goal_repo.delete(goal_id)

    note = note_repo.get_for_month(2026, 6)[0]
    assert note.id == note_id
    assert note.goal_id is None
