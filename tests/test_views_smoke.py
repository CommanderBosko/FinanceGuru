"""Offscreen smoke tests for the GUI layer.

The views are the one layer the pure-logic tests never touch, and a past audit
found four of them silently missing the public ``refresh()`` contract that
``MainWindow._refresh_all()`` duck-types against — a view without it just goes
stale after a DB restore or tab switch, with no error. These tests construct
every view headlessly (the session ``qapp`` fixture runs Qt on the offscreen
platform, so no display is needed) against the per-test temp database, and
lock in that contract.

Constructing views is network-safe: the Stocks / Stock Tips fetcher QThreads
only start from their explicit "Refresh Prices" button handlers, which nothing
here triggers. The Currency Converter tab is different -- it kicks off a live
rates fetch on construction -- so the `_no_currency_rates_fetch` fixture below
patches its QThread's start() to a no-op for every test in this module.
"""

from datetime import date
from decimal import Decimal

import pytest

from financeguru.models.bill import Bill
from financeguru.models.debt import Debt
from financeguru.models.expense import Expense
from financeguru.models.goal import Goal
from financeguru.models.income import Income
from financeguru.models.note import Note
from financeguru.models.payment import Payment
from financeguru.models.stock import Stock
from financeguru.models.stock_tip import StockTip
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import debts as debt_repo
from financeguru.repositories import expenses as expense_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import incomes as income_repo
from financeguru.repositories import notes as note_repo
from financeguru.repositories import payments as payment_repo
from financeguru.repositories import stock_tips as tip_repo
from financeguru.repositories import stocks as stock_repo
from financeguru.rates import RatesFetcher
from financeguru.views.bills_view import BillsView
from financeguru.views.charts_view import ChartsView
from financeguru.views.currency_converter_view import CurrencyConverterView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.debt_snowball_view import DebtSnowballView
from financeguru.views.expenses_view import ExpensesView
from financeguru.views.goals_view import GoalsView
from financeguru.views.main_window import MainWindow
from financeguru.views.notes_view import NotesView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.salary_view import SalaryView
from financeguru.views.stock_tips_view import StockTipsView
from financeguru.views.stocks_view import StocksView

EXPECTED_TABS = [
    "Dashboard",
    "Bills",
    "Charts",
    "Currency Converter",
    "Debt Snowball",
    "Expenses",
    "Goals",
    "Income",
    "Notes",
    "Payments",
    "Stock Tips",
    "Stocks",
]

# Every tab widget class, importable directly so a failure points at the view
# rather than at MainWindow.
VIEW_CLASSES = [
    DashboardView,
    BillsView,
    PaymentsView,
    ExpensesView,
    SalaryView,
    StocksView,
    StockTipsView,
    DebtSnowballView,
    GoalsView,
    ChartsView,
    CurrencyConverterView,
    NotesView,
]


@pytest.fixture(autouse=True)
def _no_currency_rates_fetch(monkeypatch):
    # Unlike Stocks/Stock Tips, the Currency Converter tab fetches on
    # construction rather than from a button, so it needs an explicit patch
    # to keep these tests hermetic and network-free. See module docstring.
    monkeypatch.setattr(RatesFetcher, "start", lambda self: None)


def _dispose(widget, qapp) -> None:
    """Release a top-level widget before the test returns.

    Widgets are kept as locals and torn down here so nothing Qt-owned survives
    to interpreter exit, where late C++ destruction can segfault.
    """
    widget.deleteLater()
    qapp.processEvents()


@pytest.fixture
def seeded_db(temp_db):
    """Representative rows in every table the views read.

    Seeded through the repositories (not raw SQL) so the Decimal<->REAL
    round-trip and column ordering match production writes.
    """
    today = date.today()
    bill_repo.add(Bill(name="Rent", amount=Decimal("1500.00"), due_day=1, recurrence="monthly"))
    bill_repo.add(
        Bill(
            name="Car Insurance",
            amount=Decimal("620.00"),
            due_day=15,
            due_month=today.month,
            recurrence="yearly",
        )
    )
    bill_repo.add(
        Bill(
            name="Passport Renewal",
            amount=Decimal("130.00"),
            due_day=20,
            due_month=today.month,
            due_year=today.year,
            recurrence="one-time",
        )
    )
    goal_bill_id = bill_repo.add(
        Bill(
            name="Goal: Vacation",
            amount=Decimal("200.00"),
            due_day=1,
            recurrence="monthly",
            category="Savings",
        )
    )
    rent_id = bill_repo.get_all()[0].id
    payment_repo.add(
        Payment(amount=Decimal("1500.00"), paid_date=today.isoformat(), bill_id=rent_id)
    )
    expense_repo.add(
        Expense(amount=Decimal("42.75"), spent_date=today.isoformat(), notes="groceries")
    )
    income_repo.add(Income(name="Bosko — Main Job", amount=Decimal("2400.00"), pay_date=today.isoformat()))
    stock_repo.add(
        Stock(
            ticker="VOO",
            shares=Decimal("3.5"),
            purchase_price=Decimal("410.22"),
            purchase_date="2026-01-15",
        )
    )
    tip_repo.add(
        StockTip(
            id=0,
            ticker="NVDA",
            action="buy",
            target_price=Decimal("180.00"),
            confidence=4,
            notes=None,
            added_date=today.isoformat(),
        )
    )
    debt_repo.add(
        Debt(
            id=0,
            name="Visa",
            balance=Decimal("1200.00"),
            interest_rate=Decimal("19.99"),
            minimum_payment=Decimal("35.00"),
            notes=None,
        )
    )
    goal_repo.add(
        Goal(
            name="Vacation",
            price=Decimal("2400.00"),
            target_date=date(today.year + 1, today.month, 1).isoformat(),
            bill_id=goal_bill_id,
        )
    )
    note_repo.add(Note(body="Seeded note", month_year=f"{today.year:04d}-{today.month:02d}"))
    note_repo.add(Note(
        body="Linked to Rent",
        month_year=f"{today.year:04d}-{today.month:02d}",
        bill_id=rent_id,
    ))
    yield temp_db


def test_main_window_has_expected_tabs_in_order(qapp):
    window = MainWindow()
    labels = [window._tabs.tabText(i) for i in range(window._tabs.count())]
    assert labels == EXPECTED_TABS
    _dispose(window, qapp)


def test_every_tab_exposes_public_refresh(qapp):
    # MainWindow._refresh_all() duck-types on `refresh`, so a view shipping
    # with only a private _refresh silently goes stale — fail loudly instead.
    window = MainWindow()
    for i in range(window._tabs.count()):
        widget = window._tabs.widget(i)
        assert callable(getattr(widget, "refresh", None)), (
            f"Tab '{window._tabs.tabText(i)}' ({type(widget).__name__}) has no "
            "public callable refresh(); MainWindow._refresh_all() will skip it "
            "and the view will go stale after a DB restore or tab switch."
        )
    _dispose(window, qapp)


def test_refresh_all_with_seeded_data(qapp, seeded_db):
    # Seeded before construction so the constructors' initial loads also
    # exercise populated tables, not just the refresh path.
    window = MainWindow()
    window._refresh_all()
    _dispose(window, qapp)


@pytest.mark.parametrize("view_cls", VIEW_CLASSES, ids=lambda cls: cls.__name__)
def test_view_constructs_and_refreshes(view_cls, qapp, seeded_db):
    view = view_cls()
    view.refresh()
    _dispose(view, qapp)


def test_notes_navigate_refreshes_the_target_view_exactly_once(qapp, seeded_db, monkeypatch):
    # _on_notes_navigate switches tabs (which alone would trigger
    # _on_tab_changed's refresh via currentChanged) AND calls select_month
    # (which also refreshes) — regression guard for both firing together and
    # doubling the DB round-trips on every link click.
    window = MainWindow()
    original_refresh = type(window._bills)._refresh
    calls = []

    def counting_refresh(self):
        calls.append(1)
        return original_refresh(self)

    monkeypatch.setattr(type(window._bills), "_refresh", counting_refresh)
    window._on_notes_navigate("bills", 2026, 6)
    assert calls == [1]
    _dispose(window, qapp)


def test_charts_net_worth_trend_renders_gapped_series(qapp, seeded_db):
    # Two runs separated by a >7-day gap: the trend chart must hold the dot
    # series plus one line per contiguous segment (never a line spanning the
    # gap), and re-render cleanly on refresh.
    from financeguru.repositories import snapshots

    for day in (date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 20), date(2026, 6, 21)):
        snapshots.capture(day)
    view = ChartsView()
    assert len(view._trend_chart.series()) == 3  # dots + 2 segment lines
    view.refresh()
    assert len(view._trend_chart.series()) == 3
    _dispose(view, qapp)
