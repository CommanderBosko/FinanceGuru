from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.repositories import bills


def _sample(name: str = "Rent", amount: Decimal = Decimal("1200.00"),
            due_day: int = 1, recurrence: str = "monthly",
            is_active: bool = True, notes: str | None = "apartment") -> Bill:
    return Bill(name=name, amount=amount, due_day=due_day, recurrence=recurrence,
                is_active=is_active, notes=notes)


def test_add_returns_id_and_get_all_round_trips():
    new_id = bills.add(_sample())
    assert new_id

    rows = bills.get_all()
    assert len(rows) == 1
    bill = rows[0]
    assert bill.id == new_id
    assert bill.name == "Rent"
    # Stored as REAL, coerced back to an exact Decimal.
    assert bill.amount == Decimal("1200.00")
    assert isinstance(bill.amount, Decimal)
    assert bill.is_active is True
    assert bill.notes == "apartment"


def test_get_all_orders_by_due_day():
    bills.add(_sample(name="Late", due_day=28))
    bills.add(_sample(name="Early", due_day=2))
    names = [b.name for b in bills.get_all()]
    assert names == ["Early", "Late"]


def test_update_persists_changes():
    bill_id = bills.add(_sample())
    edited = _sample(name="Rent (raised)", amount=Decimal("1300.50"),
                     is_active=False)
    edited.id = bill_id
    bills.update(edited)

    bill = bills.get_all()[0]
    assert bill.name == "Rent (raised)"
    assert bill.amount == Decimal("1300.50")
    assert bill.is_active is False


def test_delete_removes_bill():
    bill_id = bills.add(_sample())
    assert bill_id
    bills.delete(bill_id)
    assert bills.get_all() == []


def test_due_month_round_trips_and_defaults_to_none():
    # Monthly bills carry no due_month.
    monthly_id = bills.add(_sample())
    monthly = next(b for b in bills.get_all() if b.id == monthly_id)
    assert monthly.due_month is None

    # A yearly bill stores its month, and it survives an update.
    yearly = Bill(name="Car Insurance", amount=Decimal("900.00"), due_day=15,
                  due_month=3, recurrence="yearly")
    yearly_id = bills.add(yearly)
    loaded = next(b for b in bills.get_all() if b.id == yearly_id)
    assert loaded.due_month == 3

    loaded.due_month = 11
    bills.update(loaded)
    reloaded = next(b for b in bills.get_all() if b.id == yearly_id)
    assert reloaded.due_month == 11


def test_category_round_trips_and_defaults_to_other():
    # Explicit category survives add/get_all.
    with_cat = Bill(name="Internet", amount=Decimal("60.00"), due_day=10,
                    category="Utilities")
    cat_id = bills.add(with_cat)
    bill = next(b for b in bills.get_all() if b.id == cat_id)
    assert bill.category == "Utilities"

    # Omitting category falls back to the model default "Other".
    default_id = bills.add(Bill(name="Misc", amount=Decimal("5.00"), due_day=20))
    default_bill = next(b for b in bills.get_all() if b.id == default_id)
    assert default_bill.category == "Other"

    # Updating the category persists.
    bill.category = "Internet & Phone"
    bills.update(bill)
    reloaded = next(b for b in bills.get_all() if b.id == cat_id)
    assert reloaded.category == "Internet & Phone"
