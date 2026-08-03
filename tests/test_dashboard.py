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


def test_due_day_31_clamps_to_shorter_months_actual_last_day(qapp, monkeypatch):
    # Regression: a goal mirrored into a monthly Bill derives due_day from
    # its target month (e.g. December -> 31), but the dashboard evaluates
    # that Bill against whatever month is *currently* being viewed. A naive
    # ``bill.due_day < today.day`` comparison can never trigger in a
    # shorter month (today.day tops out at 28 in February), so the bill
    # silently never shows as due/overdue all month long. February 2026 is
    # not a leap year, so it has 28 days.
    import financeguru.views.dashboard_view as dashboard_view

    class _FixedFeb(date):
        @classmethod
        def today(cls):
            return cls(2026, 2, 28)

    monkeypatch.setattr(dashboard_view, "date", _FixedFeb)

    bills.add(Bill(name="Goal: laptop", amount=Decimal("100.00"), due_day=31))

    view = _make_view()
    rows = _rows(view)
    # Clamped to February's real last day (28), and correctly flagged due
    # on that day rather than perpetually showing the impossible "31".
    assert rows["Goal: laptop"] == ("28", "Due on 28")


def test_due_day_31_not_yet_due_before_shorter_months_last_day(qapp, monkeypatch):
    # One day before the clamped due day, the same bill must not be flagged
    # due/overdue yet.
    import financeguru.views.dashboard_view as dashboard_view

    class _FixedFeb(date):
        @classmethod
        def today(cls):
            return cls(2026, 2, 27)

    monkeypatch.setattr(dashboard_view, "date", _FixedFeb)

    bills.add(Bill(name="Goal: laptop", amount=Decimal("100.00"), due_day=31))

    view = _make_view()
    rows = _rows(view)
    assert rows["Goal: laptop"] == ("28", "Due on 28")


def test_due_day_31_clamps_in_april(qapp, monkeypatch):
    # April has 30 days (the other shorter-month example from the bug
    # report, alongside February). A clamped due_day can only ever reach
    # "due today" (never "overdue") within the same month it clamps in,
    # since the clamp ceiling (last_day_this_month) and today.day's maximum
    # are the same value — genuine "overdue" only arises when due_day is
    # already <= the month length (see test_monthly_bills_keep_existing_behavior).
    import financeguru.views.dashboard_view as dashboard_view

    class _FixedApr(date):
        @classmethod
        def today(cls):
            return cls(2026, 4, 30)

    monkeypatch.setattr(dashboard_view, "date", _FixedApr)

    bills.add(Bill(name="Goal: laptop", amount=Decimal("100.00"), due_day=31))

    view = _make_view()
    rows = _rows(view)
    assert rows["Goal: laptop"] == ("30", "Due on 30")


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
