"""Daily net-worth snapshot capture and history.

The net-worth trend can't be back-filled — nothing else stores historical
balances — so :func:`capture` runs on every app launch and again after each
completed price refresh, upserting the current calendar day's row (last write
of the day wins). Gaps on days the app never launches are expected; the series
is per-machine, like the database itself.

Deleting a goal cascade-deletes its linked bill and that bill's payments, so an
achieved goal's contributions drop out of *future* snapshots (the set-aside
cash was presumably spent on the goal); rows already written are history and
keep their values.
"""

from datetime import date

from financeguru.db import get_connection
from financeguru.models.snapshot import Snapshot
from financeguru.money import ZERO, to_decimal


def capture(today: date | None = None) -> Snapshot:
    """Compute the tracked net worth and upsert it as ``today``'s snapshot."""
    today = today or date.today()
    with get_connection() as conn:
        stock_value = ZERO
        for row in conn.execute("SELECT shares, purchase_price, last_price FROM stocks"):
            price = row["last_price"] if row["last_price"] is not None else row["purchase_price"]
            stock_value += to_decimal(row["shares"]) * to_decimal(price)

        # Sum in Decimal on the Python side (project convention) rather than
        # SQL SUM, which would accumulate in binary floating point.
        debt_total = ZERO
        for row in conn.execute("SELECT balance FROM debts"):
            debt_total += to_decimal(row["balance"])

        goal_savings = ZERO
        for row in conn.execute(
            "SELECT p.amount FROM payments p JOIN goals g ON p.bill_id = g.bill_id"
        ):
            goal_savings += to_decimal(row["amount"])

        snap = Snapshot(
            snap_date=today.isoformat(),
            stock_value=stock_value,
            debt_total=debt_total,
            goal_savings=goal_savings,
            net_worth=stock_value - debt_total + goal_savings,
        )
        conn.execute(
            """INSERT INTO snapshots (snap_date, stock_value, debt_total, goal_savings, net_worth)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(snap_date) DO UPDATE SET
                   stock_value = excluded.stock_value,
                   debt_total = excluded.debt_total,
                   goal_savings = excluded.goal_savings,
                   net_worth = excluded.net_worth""",
            (snap.snap_date, snap.stock_value, snap.debt_total,
             snap.goal_savings, snap.net_worth),
        )
    return snap


def get_all() -> list[Snapshot]:
    """All snapshots, oldest first — the order a trend chart consumes them."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM snapshots ORDER BY snap_date").fetchall()
    return [_row_to_snapshot(r) for r in rows]


# Consecutive snapshots at most this many days apart are considered one
# contiguous run for trend drawing. A week covers the realistic launch cadence
# (the app snapshots only on days it runs); anything longer is a genuine gap
# the chart must show as a break rather than interpolate across.
MAX_TREND_GAP_DAYS = 7


def trend_segments(
    snaps: list[Snapshot], max_gap_days: int = MAX_TREND_GAP_DAYS
) -> list[list[Snapshot]]:
    """Split a snapshot series into contiguous runs for honest gap rendering.

    Returns oldest-first segments; a new segment starts wherever two adjacent
    snapshots are more than ``max_gap_days`` apart. The chart draws each
    segment as its own connected line (a single-snapshot segment renders as a
    lone point), so days the app never ran appear as visible breaks instead of
    a line pretending the value was known in between. Pure — sorts its input,
    touches no database.
    """
    ordered = sorted(snaps, key=lambda s: s.snap_date)
    segments: list[list[Snapshot]] = []
    previous: date | None = None
    for snap in ordered:
        day = date.fromisoformat(snap.snap_date)
        if previous is None or (day - previous).days > max_gap_days:
            segments.append([])
        segments[-1].append(snap)
        previous = day
    return segments


def _row_to_snapshot(row) -> Snapshot:
    return Snapshot(
        id=row["id"],
        snap_date=row["snap_date"],
        stock_value=to_decimal(row["stock_value"]),
        debt_total=to_decimal(row["debt_total"]),
        goal_savings=to_decimal(row["goal_savings"]),
        net_worth=to_decimal(row["net_worth"]),
    )
