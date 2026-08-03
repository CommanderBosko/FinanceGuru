from decimal import Decimal

from financeguru.models.income import Income
from financeguru.repositories import incomes


def test_add_and_round_trip():
    new_id = incomes.add(Income(name="Bosko — Main Job", amount=Decimal("2500.00"),
                                pay_day=15, notes="net pay"))
    assert new_id

    rows = incomes.get_all()
    assert len(rows) == 1
    inc = rows[0]
    assert inc.name == "Bosko — Main Job"
    assert inc.amount == Decimal("2500.00")
    assert inc.pay_day == 15
    assert isinstance(inc.amount, Decimal)


def test_get_all_orders_by_name():
    incomes.add(Income(name="Zeta", amount=Decimal("1"), pay_day=1))
    incomes.add(Income(name="Alpha", amount=Decimal("1"), pay_day=1))
    assert [i.name for i in incomes.get_all()] == ["Alpha", "Zeta"]


def test_update_and_delete():
    iid = incomes.add(Income(name="Side gig", amount=Decimal("300"), pay_day=1))
    incomes.update(Income(id=iid, name="Side gig", amount=Decimal("400"),
                          pay_day=5, notes="raise"))
    inc = incomes.get_all()[0]
    assert inc.amount == Decimal("400")
    assert inc.pay_day == 5
    assert inc.notes == "raise"

    incomes.delete(iid)
    assert incomes.get_all() == []
