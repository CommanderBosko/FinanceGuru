"""Behavioral tests for MainWindow's global month selector.

One QComboBox in a toolbar row above the QTabWidget replaces the per-tab
month pickers Bills, Payments, Expenses, Income, Goals, Notes, and Charts'
pie chart used to each own independently — see the Project Brief this was
built from. These tests exercise the wiring itself (the union-building,
broadcasting, and the Notes/Charts "ignore All" exception); each affected
tab's own filtering RULE is already covered by its own test file
(test_bills_view.py, test_goals_view.py, test_payments_view.py,
test_expenses_view.py, test_salary_view.py, test_notes_view.py,
test_charts_view.py, test_stock_tips_view.py).

Construction of every tab (including the Currency Converter, which kicks off
a live rates fetch on construction) mirrors test_views_smoke.py's own
network-safety guard.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.note import Note
from financeguru.models.payment import Payment
from financeguru.models.stock_tip import StockTip
from financeguru.rates import RatesFetcher
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import notes as note_repo
from financeguru.repositories import payments as payment_repo
from financeguru.repositories import stock_tips as tip_repo
from financeguru.views.main_window import MainWindow


@pytest.fixture(autouse=True)
def _no_currency_rates_fetch(monkeypatch):
    monkeypatch.setattr(RatesFetcher, "start", lambda self: None)


@pytest.fixture
def window(qapp, temp_db):
    window = MainWindow()
    yield window
    window.deleteLater()
    qapp.processEvents()


def _labels(window) -> list[str]:
    combo = window._month_picker
    return [combo.itemText(i) for i in range(combo.count())]


def _select(window, label: str) -> None:
    window._month_picker.setCurrentIndex(_labels(window).index(label))


def test_global_picker_defaults_to_all_plus_current_month(window):
    today = date.today()
    labels = _labels(window)
    assert labels[0] == "All"
    assert today.strftime("%B %Y") in labels
    assert window._month_picker.currentData() == (today.year, today.month)


def test_construction_broadcasts_the_current_month_to_every_consumer(window):
    today = date.today()
    key = (today.year, today.month)
    assert window._bills._current_key == key
    assert window._payments._current_key == key
    assert window._expenses._current_key == key
    assert window._salary._current_key == key
    assert window._goals._current_key == key
    assert window._notes._current_key == key
    assert window._charts._current_key == key
    assert window._stock_tips._current_key == key


def test_global_list_is_the_union_of_every_contributing_tab(window):
    # A payment from January 2025 has nothing to do with Bills, Goals,
    # Charts, etc., but must still surface in the global list — "no tab
    # loses reach to a month it can currently show".
    payment_repo.add(Payment(amount=Decimal("10.00"), paid_date="2025-01-15"))
    window._rebuild_month_list()
    assert "January 2025" in _labels(window)


def test_selecting_a_month_uninteresting_to_bills_does_not_silently_fall_back_to_all(window):
    # Regression: Bills/Goals have their own "fall back to All if this exact
    # month isn't one of my own populated entries" contract (needed for
    # Notes-tab link navigation — see their own select_month docstrings).
    # The global broadcast must NOT trigger that fallback, or the toolbar
    # could show a specific month (e.g. one only relevant to Payments) while
    # Bills/Goals silently render every bill/goal ever underneath it.
    payment_repo.add(Payment(amount=Decimal("10.00"), paid_date="2025-01-15"))
    window._rebuild_month_list()

    _select(window, "January 2025")

    assert window._month_picker.currentData() == (2025, 1)
    assert window._bills._current_key == (2025, 1)   # literal, not None/"All"
    assert window._goals._current_key == (2025, 1)


def test_selecting_a_month_drives_bills_notes_and_charts_pie_together(window):
    bill_repo.add(Bill(name="Car Registration", amount=Decimal("200"), due_day=10,
                        due_month=9, recurrence="yearly"))
    # Realistic stand-in for a tab switch noticing data added via another
    # path — raw repo writes alone don't push anything to an already-built
    # view, exactly like the pre-existing per-tab-picker design this
    # replaces (see _on_tab_changed).
    window._bills.refresh()
    window._rebuild_month_list()

    # Bills' own _month_entries seeds this year's occurrence of a yearly
    # bill's due month, so it's guaranteed to be in the global union.
    year = date.today().year
    _select(window, f"September {year}")

    assert window._bills._current_key == (year, 9)
    assert window._notes._current_key == (year, 9)
    assert window._charts._current_key == (year, 9)
    assert any(b.name == "Car Registration" for b in window._bills._bills)


def test_selecting_all_leaves_notes_and_charts_pie_on_their_last_month(window):
    today = date.today()
    window._broadcast_month((2026, 3))
    assert window._notes._current_key == (2026, 3)
    assert window._charts._current_key == (2026, 3)

    window._broadcast_month(None)

    # All-aware tabs go to "All" (None) ...
    assert window._bills._current_key is None
    assert window._payments._current_key is None
    assert window._expenses._current_key is None
    assert window._salary._current_key is None
    assert window._goals._current_key is None
    assert window._stock_tips._current_key is None
    # ... but Notes and Charts' pie ignore it and keep showing March 2026.
    assert window._notes._current_key == (2026, 3)
    assert window._charts._current_key == (2026, 3)


def test_switching_to_charts_after_an_out_of_window_month_does_not_diverge(window):
    # Regression: ChartsView.refresh() used to silently reset _current_key
    # to the newest window month whenever the selection fell outside its
    # 12-month rolling window. Switching TO the Charts tab calls its
    # refresh() (see _on_tab_changed) — before the fix, that alone would
    # silently jump the pie chart to "today" while the toolbar kept showing
    # the originally selected month.
    window._broadcast_month((2020, 1))
    assert window._charts._current_key == (2020, 1)

    window._tabs.setCurrentWidget(window._charts)

    assert window._charts._current_key == (2020, 1)


def test_stock_tips_is_filtered_by_the_global_month(window):
    tip_repo.add(StockTip(id=0, ticker="NVDA", action="Buy", target_price=Decimal("180.00"),
                          confidence=4, notes=None, added_date="2026-01-01"))
    window._stock_tips.refresh()
    window._broadcast_month((2026, 1))
    assert window._stock_tips._table.rowCount() == 1

    window._broadcast_month((2026, 2))
    assert window._stock_tips._table.rowCount() == 0

    window._broadcast_month(None)
    assert window._stock_tips._table.rowCount() == 1


def test_notes_link_navigation_syncs_the_global_display_without_double_refresh(window, monkeypatch):
    today = date.today()
    bill_id = bill_repo.add(Bill(name="Rent", amount=Decimal("1000"), due_day=1, recurrence="monthly"))
    note_repo.add(Note(body="About rent", month_year=f"{today.year:04d}-{today.month:02d}", bill_id=bill_id))
    window._notes.refresh()

    original_refresh = type(window._bills)._refresh
    calls = []

    def counting_refresh(self):
        calls.append(1)
        return original_refresh(self)

    monkeypatch.setattr(type(window._bills), "_refresh", counting_refresh)

    button = window._notes._table.cellWidget(0, 2)
    assert button is not None
    button.click()

    # Bills refreshed exactly once (its own select_month call) — the global
    # picker's display sync must not trigger a second one.
    assert calls == [1]
    today = date.today()
    assert window._month_picker.currentData() == (today.year, today.month)


def test_notes_link_navigation_propagates_the_new_month_to_every_other_tab(window):
    # Regression: a note link to a Bill/Goal due in a DIFFERENT month than the
    # one currently selected used to update the destination tab and the
    # toolbar's own display, but leave every other consumer (Notes itself
    # included) filtering on the stale old key — nothing would notice on the
    # next tab switch, since _rebuild_month_list's change-detection compares
    # the toolbar's own already-synced value against itself.
    bill_id = bill_repo.add(Bill(name="Registration", amount=Decimal("50"), due_day=1,
                                  due_month=9, recurrence="yearly"))
    note_repo.add(Note(body="About registration", month_year="2026-03", bill_id=bill_id))
    window._notes.select_month(2026, 3)
    window._rebuild_month_list()

    button = window._notes._table.cellWidget(0, 2)
    assert button is not None
    button.click()

    # Mirrors _bill_target_month's own "hasn't passed yet" rule for a yearly
    # bill (see notes_view.py) rather than hardcoding a year.
    today = date.today()
    target_year = today.year if 9 >= today.month else today.year + 1
    target = (target_year, 9)
    assert window._bills._current_key == target
    assert window._month_picker.currentData() == target
    # Every other month-aware tab — Notes included, even though it's the tab
    # the click originated from and isn't the navigation's destination —
    # must agree with the toolbar, not keep showing where it was before.
    assert window._notes._current_key == target
    assert window._payments._current_key == target
    assert window._expenses._current_key == target
    assert window._salary._current_key == target
    assert window._goals._current_key == target
    assert window._charts._current_key == target
    assert window._stock_tips._current_key == target


def test_rebuild_month_list_is_a_noop_when_the_selection_is_unaffected(window, monkeypatch):
    # Rebuilding on every tab switch must not refresh every consumer tab
    # unless the selection actually needs to change.
    calls = []
    for attr in ("_bills", "_payments", "_expenses", "_salary", "_goals", "_stock_tips"):
        view = getattr(window, attr)
        monkeypatch.setattr(type(view), "select_all", lambda self, a=attr: calls.append(a))
        monkeypatch.setattr(type(view), "select_month", lambda self, y, m, a=attr: calls.append(a))

    window._rebuild_month_list()
    assert calls == []
