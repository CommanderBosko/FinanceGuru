from decimal import Decimal

from financeguru.models.income import Income
from financeguru.repositories import incomes


def test_add_and_round_trip():
    new_id = incomes.add(Income(name="Bosko — Main Job", amount=Decimal("2500.00"),
                                frequency="biweekly", notes="net pay"))
    assert new_id

    rows = incomes.get_all()
    assert len(rows) == 1
    inc = rows[0]
    assert inc.name == "Bosko — Main Job"
    assert inc.amount == Decimal("2500.00")
    assert inc.frequency == "biweekly"
    assert inc.pay_days is None
    assert isinstance(inc.amount, Decimal)


def test_specific_days_pay_days_persist():
    incomes.add(Income(name="Natty — Salary", amount=Decimal("1500"),
                       frequency="specific days", pay_days="1,15"))
    inc = incomes.get_all()[0]
    assert inc.frequency == "specific days"
    assert inc.pay_days == "1,15"


def test_get_all_orders_by_name():
    incomes.add(Income(name="Zeta", amount=Decimal("1"), frequency="monthly"))
    incomes.add(Income(name="Alpha", amount=Decimal("1"), frequency="monthly"))
    assert [i.name for i in incomes.get_all()] == ["Alpha", "Zeta"]


def test_update_and_delete():
    iid = incomes.add(Income(name="Side gig", amount=Decimal("300"),
                             frequency="monthly"))
    incomes.update(Income(id=iid, name="Side gig", amount=Decimal("400"),
                          frequency="weekly", pay_days=None, notes="raise"))
    inc = incomes.get_all()[0]
    assert inc.amount == Decimal("400")
    assert inc.frequency == "weekly"
    assert inc.notes == "raise"

    incomes.delete(iid)
    assert incomes.get_all() == []
