from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.repositories import bills, goals


def test_add_and_round_trip():
    new_id = goals.add(Goal(name="New laptop", price=Decimal("1500.00"),
                            target_date="2026-12-31", notes="work machine"))
    assert new_id

    rows = goals.get_all()
    assert len(rows) == 1
    g = rows[0]
    assert g.id == new_id
    assert g.name == "New laptop"
    assert g.price == Decimal("1500.00")
    assert g.target_date == "2026-12-31"
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
