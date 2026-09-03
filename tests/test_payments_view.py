"""Behavioral tests for the Payments tab's month filter and live search.

The construction/refresh contract is covered by test_views_smoke; these tests
drive the two filters (mirroring the Expenses tab) against a seeded table and
assert on the visible row set. PaymentsView no longer owns a month-picker
widget — the global month selector in MainWindow now owns the combo (see
test_main_window_global_month.py) and drives this tab via
select_month()/select_all(); these tests exercise that same surface directly.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.payment import Payment
from financeguru.repositories import payments as payment_repo
from financeguru.views.payments_view import PaymentsView


@pytest.fixture
def view(qapp, temp_db):
    today = date.today()
    payment_repo.add(Payment(amount=Decimal("42.75"), paid_date=today.isoformat(),
                             notes="rent"))
    payment_repo.add(Payment(amount=Decimal("12.00"), paid_date=today.isoformat(),
                             notes=None))
    payment_repo.add(Payment(amount=Decimal("99.99"), paid_date="2025-01-15",
                             notes="old power bill"))
    view = PaymentsView()
    yield view
    view.deleteLater()
    qapp.processEvents()


def test_defaults_to_current_month_only(view):
    assert view._table.rowCount() == 2
    assert view._current_key == (date.today().year, date.today().month)


def test_month_keys_span_from_earliest_record_to_now(view):
    keys = view.month_keys()
    assert (2025, 1) in keys
    assert (date.today().year, date.today().month) in keys


def test_selecting_all_shows_full_history(view):
    view.select_all()
    assert view._table.rowCount() == 3


def test_selecting_a_past_month_shows_only_that_month(view):
    view.select_month(2025, 1)
    assert view._table.rowCount() == 1
    assert view._table.item(0, 3).text() == "old power bill"


def test_search_filters_across_display_fields(view):
    view.select_all()

    view._search.setText("power")            # notes
    assert view._table.rowCount() == 1
    assert view._table.item(0, 3).text() == "old power bill"

    view._search.setText("$12.00")           # displayed amount
    assert view._table.rowCount() == 1

    view._search.setText("no such thing")
    assert view._table.rowCount() == 0

    view._search.clear()
    assert view._table.rowCount() == 3


def test_search_chains_with_month_filter(view):
    # "power" is on last year's payment; with the current-month filter still
    # active, it must stay hidden even though search alone would match it.
    view._search.setText("power")
    assert view._table.rowCount() == 0
