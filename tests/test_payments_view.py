"""Behavioral tests for the Payments tab's month filter and live search.

The construction/refresh contract is covered by test_views_smoke; these tests
drive the two filters (mirroring the Expenses tab) against a seeded table and
assert on the visible row set.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.payment import Payment
from financeguru.repositories import payments as payment_repo
from financeguru.views.payments_view import PaymentsView

_ALL_MONTHS_INDEX = 0  # index 0 is always the "All" entry; index 1 is the current month


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
    assert view._month_picker.currentIndex() == 1
    assert view._month_picker.currentText() == date.today().strftime("%B %Y")


def test_month_picker_spans_from_earliest_record_to_now(view):
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    assert labels[0] == "All"
    assert labels[-1] == "January 2025"
    assert labels[1] == date.today().strftime("%B %Y")


def test_selecting_all_shows_full_history(view):
    view._month_picker.setCurrentIndex(_ALL_MONTHS_INDEX)
    assert view._table.rowCount() == 3


def test_selecting_a_past_month_shows_only_that_month(view):
    labels = [view._month_picker.itemText(i) for i in range(view._month_picker.count())]
    view._month_picker.setCurrentIndex(labels.index("January 2025"))
    assert view._table.rowCount() == 1
    assert view._table.item(0, 3).text() == "old power bill"


def test_search_filters_across_display_fields(view):
    view._month_picker.setCurrentIndex(_ALL_MONTHS_INDEX)

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
