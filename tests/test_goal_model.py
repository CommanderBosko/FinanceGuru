from datetime import date
from decimal import Decimal

from financeguru.models.goal import Goal, months_remaining


# A fixed "today" keeps these tests deterministic regardless of the run date.
TODAY = date(2026, 6, 14)


def test_months_remaining_counts_calendar_months():
    assert months_remaining("2026-12-31", TODAY) == 6
    assert months_remaining("2027-06-30", TODAY) == 12


def test_months_remaining_floors_at_one_for_current_month():
    # Same month as today must yield one contribution, not zero.
    assert months_remaining("2026-06-30", TODAY) == 1


def test_months_remaining_floors_at_one_for_past_dates():
    # A target already in the past still yields a single contribution
    # rather than a negative count (which would break monthly_savings).
    assert months_remaining("2026-01-01", TODAY) == 1


def test_monthly_savings_divides_price_over_months():
    goal = Goal(name="Laptop", price=Decimal("1200.00"), target_date="2026-12-31")
    # 6 months remaining -> 1200 / 6 = 200.00
    assert goal.monthly_savings(TODAY) == Decimal("200.00")


def test_monthly_savings_rounds_up_to_the_cent():
    # 1000 / 6 = 166.666... must round UP so contributions fully fund the price.
    goal = Goal(name="Fund", price=Decimal("1000.00"), target_date="2026-12-31")
    assert goal.monthly_savings(TODAY) == Decimal("166.67")


def test_monthly_savings_returns_full_price_when_due_now():
    goal = Goal(name="Urgent", price=Decimal("500.00"), target_date="2026-06-30")
    assert goal.monthly_savings(TODAY) == Decimal("500.00")
