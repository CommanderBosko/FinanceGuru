from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.note import Note
from financeguru.repositories import bills, goals, notes


def test_add_and_round_trip():
    new_id = goals.add(Goal(name="New laptop", price=Decimal("1500.00"),
                            target_date="2026-12-31", start_date="2026-06-01",
                            notes="work machine"))
    assert new_id

    rows = goals.get_all()
    assert len(rows) == 1
    g = rows[0]
    assert g.id == new_id
    assert g.name == "New laptop"
    assert g.price == Decimal("1500.00")
    assert g.target_date == "2026-12-31"
    assert g.start_date == "2026-06-01"
    assert g.bill_id is None
    assert isinstance(g.price, Decimal)


def test_get_all_orders_by_target_date():
    goals.add(Goal(name="Later", price=Decimal("100"), target_date="2027-01-31"))
    goals.add(Goal(name="Sooner", price=Decimal("100"), target_date="2026-06-30"))
    assert [g.name for g in goals.get_all()] == ["Sooner", "Later"]


def test_update_and_delete():
    gid = goals.add(Goal(name="Vacation", price=Decimal("3000"),
                         target_date="2026-09-30"))
    goals.update(Goal(id=gid, name="Vacation", price=Decimal("3500.00"),
                      target_date="2026-10-31", notes="upgraded"))
    g = goals.get_all()[0]
    assert g.price == Decimal("3500.00")
    assert g.target_date == "2026-10-31"
    assert g.notes == "upgraded"

    goals.delete(gid)
    assert goals.get_all() == []


def test_delete_default_leaves_linked_notes_with_link_cleared():
    gid = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31"))
    note_id = notes.add(Note(body="About the car goal", month_year="2026-06", goal_id=gid))

    goals.delete(gid)

    note = notes.get_for_month(2026, 6)[0]
    assert note.id == note_id
    assert note.goal_id is None


def test_delete_with_delete_linked_notes_removes_them_atomically():
    gid = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31"))
    notes.add(Note(body="About the car goal", month_year="2026-06", goal_id=gid))

    goals.delete(gid, delete_linked_notes=True)

    assert goals.get_all() == []
    assert notes.get_by_goal_id(gid) == []


def test_deleting_linked_bill_sets_goal_bill_id_null():
    # goals.bill_id is declared ON DELETE SET NULL, so removing the linked bill
    # leaves the goal intact rather than cascading it away.
    bill_id = bills.add(Bill(name="Goal: car", amount=Decimal("200"), due_day=1))
    assert bill_id
    gid = goals.add(Goal(name="Car", price=Decimal("2400"),
                         target_date="2027-01-31", bill_id=bill_id))
    bills.delete(bill_id)

    survivors = goals.get_all()
    assert len(survivors) == 1
    assert survivors[0].id == gid
    assert survivors[0].bill_id is None


# ── Atomic goal+bill operations ─────────────────────────────────────────────
# GoalsView used to do these as two separate get_connection() calls (one per
# repo); a failure between them could leave a phantom ownerless Bill or an
# orphaned Goal. add_with_bill/update_with_bill/delete_with_bill wrap both
# writes in a single transaction instead.

def test_add_with_bill_inserts_both_and_links_them():
    goal = Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31",
                start_date="2026-01-01")
    bill = Bill(name="Goal: Car", amount=Decimal("200"), due_day=31)

    goal_id, bill_id = goals.add_with_bill(goal, bill)

    assert goal_id and bill_id
    assert goal.bill_id == bill_id  # mutated in place before the goal insert
    saved_goal = goals.get_all()[0]
    assert saved_goal.id == goal_id
    assert saved_goal.bill_id == bill_id
    assert len(bills.get_all()) == 1


def test_add_with_bill_rolls_back_the_bill_if_the_goal_insert_fails(monkeypatch):
    class _Boom(Exception):
        pass

    def _boom(*args, **kwargs):
        raise _Boom("simulated failure between the two writes")

    monkeypatch.setattr(goals, "add", _boom)

    goal = Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31",
                start_date="2026-01-01")
    bill = Bill(name="Goal: Car", amount=Decimal("200"), due_day=31)

    with pytest.raises(_Boom):
        goals.add_with_bill(goal, bill)

    # The bill insert ran first and succeeded — without the shared
    # transaction it would be a permanent phantom, ownerless Bill.
    assert bills.get_all() == []
    assert goals.get_all() == []


def test_update_with_bill_new_inserts_a_bill_and_links_it():
    goal_id = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31"))
    goal = goals.get_all()[0]
    assert goal.bill_id is None

    bill = Bill(name="Goal: Car", amount=Decimal("200"), due_day=31)
    goals.update_with_bill(goal, bill, bill_is_new=True)

    updated = goals.get_all()[0]
    assert updated.bill_id is not None
    assert len(bills.get_all()) == 1


def test_update_with_bill_existing_updates_in_place():
    bill_id = bills.add(Bill(name="Goal: Car", amount=Decimal("200"), due_day=31))
    goal_id = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31",
                              bill_id=bill_id))
    goal = goals.get_all()[0]

    updated_bill = Bill(id=bill_id, name="Goal: Car", amount=Decimal("250"), due_day=31)
    goal.price = Decimal("3000")
    goals.update_with_bill(goal, updated_bill, bill_is_new=False)

    assert goals.get_all()[0].price == Decimal("3000")
    assert len(bills.get_all()) == 1
    assert bills.get_all()[0].amount == Decimal("250")


def test_delete_with_bill_removes_both():
    bill_id = bills.add(Bill(name="Goal: Car", amount=Decimal("200"), due_day=31))
    gid = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31",
                          bill_id=bill_id))

    goals.delete_with_bill(gid, bill_id)

    assert goals.get_all() == []
    assert bills.get_all() == []


def test_delete_with_bill_none_only_removes_the_goal():
    gid = goals.add(Goal(name="Car", price=Decimal("2400"), target_date="2027-01-31"))

    goals.delete_with_bill(gid, None)

    assert goals.get_all() == []
