from financeguru.db import get_connection
from financeguru.models.stock_tip import StockTip


def _row_to_tip(row) -> StockTip:
    return StockTip(
        id=row["id"],
        ticker=row["ticker"],
        action=row["action"],
        target_price=row["target_price"],
        confidence=row["confidence"],
        notes=row["notes"],
        added_date=row["added_date"],
        analyst_action=row["analyst_action"],
        analyst_target=row["analyst_target"],
        analyst_count=row["analyst_count"],
        analyst_updated=row["analyst_updated"],
    )


def get_all() -> list[StockTip]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM stock_tips ORDER BY ticker"
        ).fetchall()
    return [_row_to_tip(r) for r in rows]


def add(tip: StockTip) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO stock_tips
               (ticker, action, target_price, confidence, notes, added_date,
                analyst_action, analyst_target, analyst_count, analyst_updated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (tip.ticker, tip.action, tip.target_price, tip.confidence,
             tip.notes, tip.added_date, tip.analyst_action, tip.analyst_target,
             tip.analyst_count, tip.analyst_updated),
        )
        return cur.lastrowid or 0


def update(tip: StockTip) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE stock_tips SET
               ticker=?, action=?, target_price=?, confidence=?, notes=?,
               analyst_action=?, analyst_target=?, analyst_count=?, analyst_updated=?
               WHERE id=?""",
            (tip.ticker, tip.action, tip.target_price, tip.confidence, tip.notes,
             tip.analyst_action, tip.analyst_target, tip.analyst_count,
             tip.analyst_updated, tip.id),
        )


def update_analyst_data(tip_id: int, action: str | None, target: float | None,
                        count: int | None, updated: str) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE stock_tips SET
               analyst_action=?, analyst_target=?, analyst_count=?, analyst_updated=?
               WHERE id=?""",
            (action, target, count, updated, tip_id),
        )


def delete(tip_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM stock_tips WHERE id=?", (tip_id,))
