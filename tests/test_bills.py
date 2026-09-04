from datetime import date
from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.note import Note
from financeguru.repositories import bills, notes


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


def test_get_all_places_yearly_and_one_time_bills_by_actual_due_distance():
    # Regression for interleaving bug: a plain `ORDER BY due_day` would put
    # the December one-time bill (due_day=5) before the monthly bill
    # (due_day=20) even though, viewed from January, December is 11 months
    # away — nowhere near "soonest". Bill.due_sort_key fixes that by using
    # months-until-next-occurrence as the primary key.
    today = date(2026, 1, 10)

    bills.add(_sample(name="Monthly", due_day=20, recurrence="monthly"))
    bills.add(Bill(name="December One-Time", amount=Decimal("400"), due_day=5,
                    due_month=12, due_year=2026, recurrence="one-time"))
    bills.add(Bill(name="March Yearly", amount=Decimal("900"), due_day=1,
                    due_month=3, recurrence="yearly"))
    bills.add(Bill(name="Overdue One-Time", amount=Decimal("50"), due_day=1,
                    due_month=11, due_year=2025, recurrence="one-time"))

    names = [b.name for b in bills.get_all(today)]
    # Overdue one-time (2 months in the past) sorts first; then the monthly
    # bill (always "this month"); then March yearly (2 months out); then the
    # December one-time bill (11 months out) sorts last.
    assert names == ["Overdue One-Time", "Monthly", "March Yearly", "December One-Time"]


def test_get_all_orders_monthly_bills_by_due_day_regardless_of_today():
    # Monthly bills stay grouped by due_day alone — their relative order must
    # not flip depending on whether "today" is before or after due_day.
    bills.add(_sample(name="Late", due_day=28, recurrence="monthly"))
    bills.add(_sample(name="Early", due_day=2, recurrence="monthly"))

    early_in_month = [b.name for b in bills.get_all(date(2026, 1, 1))]
    late_in_month = [b.name for b in bills.get_all(date(2026, 1, 25))]
    assert early_in_month == ["Early", "Late"]
    assert late_in_month == ["Early", "Late"]


def test_get_all_wraps_yearly_bill_to_next_year_once_due_month_passed():
    today = date(2026, 6, 15)
    bills.add(_sample(name="Monthly", due_day=1, recurrence="monthly"))
    bills.add(Bill(name="March Yearly (passed)", amount=Decimal("1"), due_day=1,
                    due_month=3, recurrence="yearly"))
    bills.add(Bill(name="August Yearly (upcoming)", amount=Decimal("1"), due_day=1,
                    due_month=8, recurrence="yearly"))

    names = [b.name for b in bills.get_all(today)]
    # August (2 months out) comes before March, which has already happened
    # this year and so wraps to next March (9 months out) — it does not sort
    # as if it were "overdue" ahead of the monthly bill.
    assert names == ["Monthly", "August Yearly (upcoming)", "March Yearly (passed)"]


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


def test_one_time_due_year_round_trips():
    once = Bill(name="Roof Repair", amount=Decimal("4000.00"), due_day=20,
                due_month=9, due_year=2026, recurrence="one-time")
    once_id = bills.add(once)
    loaded = next(b for b in bills.get_all() if b.id == once_id)
    assert (loaded.due_month, loaded.due_year, loaded.recurrence) == (9, 2026, "one-time")

    # Monthly/yearly bills leave due_year NULL.
    monthly_id = bills.add(_sample())
    monthly = next(b for b in bills.get_all() if b.id == monthly_id)
    assert monthly.due_year is None


def test_is_due_in_by_recurrence():
    monthly = Bill(name="Rent", amount=Decimal("1"), due_day=1)
    assert monthly.is_due_in(2026, 6) is True
    assert monthly.is_due_in(2027, 1) is True

    yearly = Bill(name="Insurance", amount=Decimal("1"), due_day=1,
                  due_month=3, recurrence="yearly")
    assert yearly.is_due_in(2026, 3) is True
    assert yearly.is_due_in(2099, 3) is True   # any year, matching month
    assert yearly.is_due_in(2026, 4) is False

    once = Bill(name="Roof", amount=Decimal("1"), due_day=1,
                due_month=9, due_year=2026, recurrence="one-time")
    assert once.is_due_in(2026, 9) is True
    assert once.is_due_in(2027, 9) is False    # right month, wrong year
    assert once.is_due_in(2026, 8) is False


def test_overdue_carryover_start_monthly_is_always_none():
    monthly = Bill(name="Rent", amount=Decimal("1"), due_day=1)
    assert monthly.overdue_carryover_start(2026, 7) is None
    assert monthly.overdue_carryover_start(2027, 1) is None


def test_overdue_carryover_start_yearly_limited_to_current_year():
    yearly = Bill(name="Insurance", amount=Decimal("1"), due_day=15,
                  due_month=3, recurrence="yearly")
    # Earlier this year → carries over.
    assert yearly.overdue_carryover_start(2026, 7) == "2026-03-01"
    # Same month or later this year → nothing missed yet.
    assert yearly.overdue_carryover_start(2026, 3) is None
    assert yearly.overdue_carryover_start(2026, 2) is None
    # December yearly viewed in January: previous years never carry over.
    december = Bill(name="Dues", amount=Decimal("1"), due_day=1,
                    due_month=12, recurrence="yearly")
    assert december.overdue_carryover_start(2027, 1) is None
    # A yearly missing its due_month can't carry over.
    no_month = Bill(name="Odd", amount=Decimal("1"), due_day=1,
                    recurrence="yearly")
    assert no_month.overdue_carryover_start(2026, 7) is None


def test_overdue_carryover_start_one_time_crosses_years():
    once = Bill(name="Roof", amount=Decimal("1"), due_day=20,
                due_month=9, due_year=2025, recurrence="one-time")
    # Past year → still carries over.
    assert once.overdue_carryover_start(2026, 7) == "2025-09-01"
    # Earlier month of the same year → carries over.
    march = Bill(name="Fix", amount=Decimal("1"), due_day=5,
                 due_month=3, due_year=2026, recurrence="one-time")
    assert march.overdue_carryover_start(2026, 7) == "2026-03-01"
    # Current month or future → nothing missed.
    assert march.overdue_carryover_start(2026, 3) is None
    assert march.overdue_carryover_start(2026, 2) is None
    assert march.overdue_carryover_start(2025, 12) is None


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


def test_delete_default_leaves_linked_notes_with_link_cleared():
    bill_id = bills.add(_sample())
    note_id = notes.add(Note(body="About the bill", month_year="2026-06", bill_id=bill_id))

    bills.delete(bill_id)

    note = notes.get_for_month(2026, 6)[0]
    assert note.id == note_id
    assert note.bill_id is None


def test_delete_with_delete_linked_notes_removes_them_atomically():
    bill_id = bills.add(_sample())
    notes.add(Note(body="About the bill", month_year="2026-06", bill_id=bill_id))

    bills.delete(bill_id, delete_linked_notes=True)

    assert bills.get_all() == []
    assert notes.get_by_bill_id(bill_id) == []
