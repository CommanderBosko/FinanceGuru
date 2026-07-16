"""Net-worth snapshot capture (`repositories/snapshots.py`).

The snapshot is the accruing data source for the future net-worth trend chart:
stock value (last fetched price, else purchase price) minus debt balances plus
cumulative goal contributions, upserted one row per calendar day.
"""

from datetime import date
from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.debt import Debt
from financeguru.models.goal import Goal
from financeguru.models.payment import Payment
from financeguru.models.stock import Stock
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import debts as debt_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import payments as payment_repo
from financeguru.repositories import snapshots
from financeguru.repositories import stocks as stock_repo


def _add_stock(ticker: str, shares: str, purchase: str,
               last_price: str | None = None) -> None:
    stock_repo.add(Stock(ticker=ticker, shares=Decimal(shares),
                         purchase_price=Decimal(purchase),
                         purchase_date="2025-01-15"))
    if last_price is not None:
        stock_repo.set_last_prices({ticker: Decimal(last_price)}, "2026-07-01")


def _add_goal_with_payments(*amounts: str) -> None:
    bill_id = bill_repo.add(Bill(name="Goal: Vacation", amount=Decimal("100"),
                                 due_day=1, category="Savings", notes="Goal"))
    goal_repo.add(Goal(name="Vacation", price=Decimal("1200"),
                       target_date="2026-12-31", bill_id=bill_id))
    for amount in amounts:
        payment_repo.add(Payment(amount=Decimal(amount), paid_date="2026-06-01",
                                 bill_id=bill_id))


def test_capture_empty_db_writes_zero_row():
    snap = snapshots.capture(date(2026, 7, 2))
    assert snap.snap_date == "2026-07-02"
    assert snap.stock_value == Decimal("0")
    assert snap.debt_total == Decimal("0")
    assert snap.goal_savings == Decimal("0")
    assert snap.net_worth == Decimal("0")
    assert len(snapshots.get_all()) == 1


def test_capture_values_stocks_at_last_price_with_purchase_fallback():
    _add_stock("AAPL", "10", "100", last_price="150.50")   # 1505.00
    _add_stock("NVDA", "2", "300")                          # never fetched: 600
    snap = snapshots.capture(date(2026, 7, 2))
    assert snap.stock_value == Decimal("2105.00")
    assert snap.net_worth == Decimal("2105.00")


def test_capture_combines_stocks_debts_and_goal_savings():
    _add_stock("AAPL", "10", "100", last_price="150.50")            # 1505.00
    debt_repo.add(Debt(id=0, name="Card", balance=Decimal("500.25"),
                       interest_rate=Decimal("19.9"),
                       minimum_payment=Decimal("25"), notes=None))
    _add_goal_with_payments("200", "100.50")                        # 300.50
    # A payment against a non-goal bill is spending, not savings.
    plain_bill = bill_repo.add(Bill(name="Rent", amount=Decimal("999"), due_day=1))
    payment_repo.add(Payment(amount=Decimal("999"), paid_date="2026-06-01",
                             bill_id=plain_bill))

    snap = snapshots.capture(date(2026, 7, 2))
    assert snap.stock_value == Decimal("1505.00")
    assert snap.debt_total == Decimal("500.25")
    assert snap.goal_savings == Decimal("300.50")
    assert snap.net_worth == Decimal("1305.25")


def test_capture_upserts_one_row_per_day():
    snapshots.capture(date(2026, 7, 2))
    _add_stock("AAPL", "1", "100")
    snap = snapshots.capture(date(2026, 7, 2))
    rows = snapshots.get_all()
    assert len(rows) == 1
    assert rows[0].stock_value == Decimal("100")
    assert snap.net_worth == Decimal("100")


def test_get_all_is_ordered_oldest_first_and_decimal():
    snapshots.capture(date(2026, 7, 2))
    snapshots.capture(date(2026, 6, 30))
    rows = snapshots.get_all()
    assert [s.snap_date for s in rows] == ["2026-06-30", "2026-07-02"]
    assert all(isinstance(s.net_worth, Decimal) for s in rows)


def _snap(day: str) -> "snapshots.Snapshot":
    from financeguru.models.snapshot import Snapshot
    zero = Decimal("0")
    return Snapshot(snap_date=day, stock_value=zero, debt_total=zero,
                    goal_savings=zero, net_worth=zero)


def test_trend_segments_empty_and_single():
    assert snapshots.trend_segments([]) == []
    lone = _snap("2026-07-01")
    assert snapshots.trend_segments([lone]) == [[lone]]


def test_trend_segments_splits_only_on_gaps_beyond_threshold():
    snaps = [
        _snap("2026-07-01"),
        _snap("2026-07-02"),
        _snap("2026-07-09"),   # exactly 7 days after the 2nd — still connected
        _snap("2026-07-17"),   # 8 days — new segment
        _snap("2026-07-18"),
    ]
    segments = snapshots.trend_segments(snaps)
    assert [[s.snap_date for s in seg] for seg in segments] == [
        ["2026-07-01", "2026-07-02", "2026-07-09"],
        ["2026-07-17", "2026-07-18"],
    ]


def test_trend_segments_sorts_input_and_honors_custom_gap():
    snaps = [_snap("2026-07-05"), _snap("2026-07-01"), _snap("2026-07-03")]
    segments = snapshots.trend_segments(snaps, max_gap_days=1)
    assert [[s.snap_date for s in seg] for seg in segments] == [
        ["2026-07-01"],
        ["2026-07-03"],
        ["2026-07-05"],
    ]


def test_deleting_a_goal_drops_its_savings_from_future_captures():
    _add_goal_with_payments("200")
    assert snapshots.capture(date(2026, 7, 1)).goal_savings == Decimal("200")
    goal = goal_repo.get_all()[0]
    goal_repo.delete(goal.id)
    bill_repo.delete(goal.bill_id)  # the view deletes the linked bill too
    # The old row is history and keeps its value; only new captures change.
    assert snapshots.capture(date(2026, 7, 2)).goal_savings == Decimal("0")
    assert snapshots.get_all()[0].goal_savings == Decimal("200")
