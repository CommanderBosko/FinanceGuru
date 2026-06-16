"""Spending aggregation for the Charts tab.

Cross-cuts payments + expenses + bills, so it lives outside any single
repository (and outside ``budget.py``, which is income/bill normalization).

The spending universe is **all payments + all expenses**. A payment against a
bill tagged with :data:`GOAL_NOTE` (a goal contribution) is force-categorized as
:data:`SAVINGS_CATEGORY`. Savings is included in the per-category breakdowns but
excluded from the headline monthly *total* — saving money isn't spending it.

All summation is done in :class:`~decimal.Decimal`; values are cast to ``float``
only at the return boundary, which is where QtCharts consumes them.
"""

from datetime import date
from decimal import Decimal

from financeguru.categories import DEFAULT_CATEGORY, GOAL_NOTE, SAVINGS_CATEGORY
from financeguru.db import get_connection
from financeguru.money import to_decimal


def _categorized_rows(conn, year: int, month: int) -> list[tuple[str, Decimal]]:
    """Return (category, amount) for every payment and expense in one month."""
    prefix = f"{year}-{month:02d}-%"
    rows: list[tuple[str, Decimal]] = []

    # Payments inherit their bill's category. A payment with no bill falls back to
    # the default; a payment against a Goal-tagged bill is treated as savings.
    for r in conn.execute(
        """
        SELECT p.amount AS amount,
               b.category AS category,
               b.notes AS bill_notes,
               p.bill_id AS bill_id
        FROM payments p
        LEFT JOIN bills b ON p.bill_id = b.id
        WHERE p.paid_date LIKE ?
        """,
        (prefix,),
    ):
        if r["bill_notes"] == GOAL_NOTE:
            category = SAVINGS_CATEGORY
        elif r["bill_id"] is None or r["category"] is None:
            category = DEFAULT_CATEGORY
        else:
            category = r["category"]
        rows.append((category, to_decimal(r["amount"])))

    for r in conn.execute(
        "SELECT amount, category FROM expenses WHERE spent_date LIKE ?",
        (prefix,),
    ):
        category = r["category"] or DEFAULT_CATEGORY
        rows.append((category, to_decimal(r["amount"])))

    return rows


def _months_ending_now(window: int) -> list[tuple[int, int]]:
    """The last ``window`` (year, month) pairs, oldest first, ending this month."""
    today = date.today()
    months: list[tuple[int, int]] = []
    y, m = today.year, today.month
    for _ in range(window):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()
    return months


def monthly_spending(window: int = 12) -> list[dict]:
    """Spending per month over the trailing ``window`` months (oldest first).

    Every month in the window is present even with no activity (zero-filled), so
    the chart's x-axis is stable regardless of how much history exists.

    Each entry::

        {
            "year": 2026, "month": 6, "label": "2026-06",
            "total": 1234.56,                       # float, Savings EXCLUDED
            "by_category": {"Food": 200.0, ...},    # float, Savings INCLUDED
        }
    """
    result: list[dict] = []
    with get_connection() as conn:
        for year, month in _months_ending_now(window):
            by_category: dict[str, Decimal] = {}
            total = Decimal("0")
            for category, amount in _categorized_rows(conn, year, month):
                by_category[category] = by_category.get(category, Decimal("0")) + amount
                if category != SAVINGS_CATEGORY:
                    total += amount
            result.append({
                "year": year,
                "month": month,
                "label": f"{year}-{month:02d}",
                "total": float(total),
                "by_category": {k: float(v) for k, v in by_category.items()},
            })
    return result


def category_breakdown(year: int, month: int) -> dict[str, float]:
    """Spending by category for a single month, including Savings.

    Categories with no spending are omitted; an empty month returns ``{}``.
    """
    with get_connection() as conn:
        totals: dict[str, Decimal] = {}
        for category, amount in _categorized_rows(conn, year, month):
            totals[category] = totals.get(category, Decimal("0")) + amount
    return {k: float(v) for k, v in totals.items()}
