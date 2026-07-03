"""Dashboard "Bills This Month" behavior, including carried-over overdue rows.

The view reads ``date.today()``, so a fixed date (2026-07-15) is patched into
the dashboard module to keep the assertions deterministic.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.payment import Payment
from financeguru.repositories import bills, payments


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch):
    import financeguru.views.dashboard_view as dashboard_view

    class _FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 7, 15)

    monkeypatch.setattr(dashboard_view, "date", _FixedDate)


def _make_view():
    from financeguru.views.dashboard_view import DashboardView

    return DashboardView()


def _rows(view) -> dict[str, tuple[str, str]]:
    """Table contents keyed by bill name: (due text, status text)."""
    table = view._bills_table
    return {
        table.item(r, 0).text(): (table.item(r, 2).text(), table.item(r, 3).text())
        for r in range(table.rowCount())
    }


def test_unpaid_past_one_time_carries_over_and_joins_totals(qapp):
    bills.add(Bill(name="Roof", amount=Decimal("500.00"), due_day=20,
                   due_month=3, due_year=2026, recurrence="one-time"))
    bills.add(Bill(name="Rent", amount=Decimal("100.00"), due_day=20))

    view = _make_view()
    rows = _rows(view)
    assert rows["Roof"] == ("Mar 20", "Overdue (Mar)")
    assert rows["Rent"] == ("20", "Due on 20")
    assert view._lbl_total.text() == "Total Bills\n$600.00"
    assert view._lbl_paid.text() == "Paid\n$0.00"
    assert view._lbl_remaining.text() == "Remaining\n$600.00"


def test_paying_a_carried_over_one_time_removes_it_on_refresh(qapp):
    roof_id = bills.add(Bill(name="Roof", amount=Decimal("500.00"), due_day=20,
                             due_month=3, due_year=2026, recurrence="one-time"))

    view = _make_view()
    assert "Roof" in _rows(view)

    payments.add(Payment(amount=Decimal("500.00"), paid_date="2026-07-01",
                         bill_id=roof_id))
    view.refresh()
    assert "Roof" not in _rows(view)
    assert view._lbl_total.text() == "Total Bills\n$0.00"


def test_one_time_paid_early_never_carries_over(qapp):
    # Any payment ever settles a one-time bill, even one made before its
    # due month.
    roof_id = bills.add(Bill(name="Roof", amount=Decimal("500.00"), due_day=20,
                             due_month=3, due_year=2026, recurrence="one-time"))
    payments.add(Payment(amount=Decimal("500.00"), paid_date="2026-01-05",
                         bill_id=roof_id))

    view = _make_view()
    assert "Roof" not in _rows(view)


def test_unpaid_earlier_this_year_yearly_carries_over(qapp):
    bills.add(Bill(name="Car Insurance", amount=Decimal("900.00"), due_day=10,
                   due_month=3, recurrence="yearly"))

    view = _make_view()
    rows = _rows(view)
    assert rows["Car Insurance"] == ("Mar 10", "Overdue (Mar)")
    assert view._lbl_remaining.text() == "Remaining\n$900.00"


def test_yearly_paid_within_its_cycle_does_not_carry_over(qapp):
    ins_id = bills.add(Bill(name="Car Insurance", amount=Decimal("900.00"),
                            due_day=10, due_month=3, recurrence="yearly"))
    payments.add(Payment(amount=Decimal("900.00"), paid_date="2026-03-12",
                         bill_id=ins_id))

    view = _make_view()
    assert "Car Insurance" not in _rows(view)


def test_yearly_paid_only_last_year_still_carries_over(qapp):
    ins_id = bills.add(Bill(name="Car Insurance", amount=Decimal("900.00"),
                            due_day=10, due_month=3, recurrence="yearly"))
    payments.add(Payment(amount=Decimal("900.00"), paid_date="2025-03-12",
                         bill_id=ins_id))

    view = _make_view()
    assert _rows(view)["Car Insurance"] == ("Mar 10", "Overdue (Mar)")


def test_future_one_time_is_absent(qapp):
    bills.add(Bill(name="Roof", amount=Decimal("500.00"), due_day=20,
                   due_month=9, due_year=2026, recurrence="one-time"))
    bills.add(Bill(name="Vacation", amount=Decimal("2000.00"), due_day=1,
                   due_month=2, due_year=2027, recurrence="one-time"))

    view = _make_view()
    assert _rows(view) == {}
    assert view._lbl_total.text() == "Total Bills\n$0.00"


def test_monthly_bills_keep_existing_behavior(qapp):
    bills.add(Bill(name="Rent", amount=Decimal("1200.00"), due_day=1))
    rent_paid_id = bills.add(Bill(name="Power", amount=Decimal("80.00"), due_day=5))
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-07-05",
                         bill_id=rent_paid_id))

    view = _make_view()
    rows = _rows(view)
    # Exactly one row each — monthly bills never gain a carried-over twin.
    assert len(rows) == 2
    assert rows["Rent"] == ("1", "Overdue")
    assert rows["Power"] == ("5", "Paid ✓")
    assert view._lbl_total.text() == "Total Bills\n$1,280.00"
    assert view._lbl_paid.text() == "Paid\n$80.00"
    assert view._lbl_remaining.text() == "Remaining\n$1,200.00"
