"""Behavioral tests for the Charts tab's pie chart month filter.

ChartsView's other two charts (the 12-month category bar view and the net
worth trend) are unaffected by the global month selector and are already
covered by test_views_smoke.py's construction/refresh checks and its
gapped-trend regression test. These tests cover only the pie chart's own
month state: it can't render "All" as content, so — like Notes — it has no
select_all(), and a globally-selected "All" is simply never forwarded to it
(see MainWindow._broadcast_month).
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.expense import Expense
from financeguru.repositories import expenses as expense_repo
from financeguru.views.charts_view import ChartsView


@pytest.fixture
def view(qapp, temp_db):
    view = ChartsView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def test_defaults_to_the_current_month(view):
    today = date.today()
    assert view._current_key == (today.year, today.month)


def test_month_keys_match_the_rolling_window(view):
    today = date.today()
    keys = view.month_keys()
    assert len(keys) == 12
    assert (today.year, today.month) in keys


def test_select_month_updates_the_pie_title_and_breakdown(view):
    today = date.today()
    expense_repo.add(Expense(amount=Decimal("50.00"), spent_date=f"{today.year:04d}-{today.month:02d}-05",
                             category="Groceries"))
    view.refresh()

    assert view._current_key == (today.year, today.month)
    assert view._pie_chart.title() == f"Category breakdown — {today.strftime('%B %Y')}"


def test_select_month_with_no_spending_shows_no_spending_title(view):
    # A month within the window but with nothing recorded — an empty pie,
    # not an error.
    today = date.today()
    prior_year, prior_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    view.select_month(prior_year, prior_month)

    label = date(prior_year, prior_month, 1).strftime("%B %Y")
    assert view._pie_chart.title() == f"Category breakdown — {label} (no spending)"


def test_select_month_outside_the_rolling_window_still_renders(view):
    # Accepted per the Project Brief: a globally-selected month outside the
    # pie's own rolling window (e.g. a future one-time bill's due month) is
    # an empty/unaffected state, not a bug — category_breakdown is queried
    # directly and doesn't depend on the window reporting.monthly_spending
    # builds month_keys() from.
    view.select_month(2099, 1)
    assert view._current_key == (2099, 1)
    assert view._pie_chart.title() == "Category breakdown — January 2099 (no spending)"


def test_refresh_keeps_a_still_valid_selection(view):
    today = date.today()
    prior_year, prior_month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    view.select_month(prior_year, prior_month)

    view.refresh()

    assert view._current_key == (prior_year, prior_month)


def test_refresh_never_resets_a_selection_outside_the_window(view):
    # Regression: refresh() must not silently reassign _current_key just
    # because the rolling window moved past it — MainWindow's global picker
    # is the sole source of truth for "which month is selected"; refresh()
    # resetting it on its own would let the toolbar and the pie chart
    # silently diverge (e.g. on a DB restore, or switching back to this tab
    # after a month outside the window was selected).
    view.select_month(2099, 1)
    assert view._current_key == (2099, 1)

    view.refresh()

    assert view._current_key == (2099, 1)


def test_month_keys_is_not_anchored_to_a_stale_self_months(view):
    # Regression: month_keys() must recompute the window fresh each call,
    # not read the cached self._months (which only updates on refresh()) —
    # otherwise a long session that never revisits this tab would keep
    # feeding MainWindow's global list a window anchored to whatever "today"
    # was at the last refresh.
    view._months = [{"year": 1999, "month": 1, "label": "1999-01", "total": 0.0, "by_category": {}}]
    keys = view.month_keys()
    assert keys != [(1999, 1)]
    today = date.today()
    assert (today.year, today.month) in keys
