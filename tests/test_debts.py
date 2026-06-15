from decimal import Decimal

from financeguru.models.debt import Debt
from financeguru.repositories import debts


def _debt(id: int = 0, name: str = "Card", balance: Decimal = Decimal("5000.00"),
          interest_rate: Decimal = Decimal("18.5"),
          minimum_payment: Decimal = Decimal("100.00"),
          notes: str | None = None) -> Debt:
    return Debt(id=id, name=name, balance=balance, interest_rate=interest_rate,
                minimum_payment=minimum_payment, notes=notes)


def test_add_and_round_trip():
    new_id = debts.add(_debt())
    assert new_id

    rows = debts.get_all()
    assert len(rows) == 1
    d = rows[0]
    assert d.id == new_id
    assert d.name == "Card"
    assert d.balance == Decimal("5000.00")
    assert d.interest_rate == Decimal("18.5")
    assert d.minimum_payment == Decimal("100.00")
    assert isinstance(d.balance, Decimal)


def test_get_all_orders_by_balance_desc():
    debts.add(_debt(name="Small", balance=Decimal("500")))
    debts.add(_debt(name="Big", balance=Decimal("9000")))
    assert [d.name for d in debts.get_all()] == ["Big", "Small"]


def test_update_and_delete():
    did = debts.add(_debt())
    debts.update(_debt(id=did, balance=Decimal("4500.00"), notes="paid down"))
    d = debts.get_all()[0]
    assert d.balance == Decimal("4500.00")
    assert d.notes == "paid down"

    debts.delete(did)
    assert debts.get_all() == []
