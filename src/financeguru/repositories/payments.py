from decimal import Decimal

from financeguru.db import get_connection
from financeguru.models.payment import Payment
from financeguru.money import to_decimal


def get_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.id, p.bill_id, p.amount, p.paid_date, p.notes,
                   b.name AS bill_name
            FROM payments p
            LEFT JOIN bills b ON p.bill_id = b.id
            ORDER BY p.paid_date DESC
        """).fetchall()
    records = []
    for r in rows:
        rec = dict(r)
        rec["amount"] = to_decimal(rec["amount"])
        records.append(rec)
    return records


def add(payment: Payment) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO payments (bill_id, amount, paid_date, notes) VALUES (?, ?, ?, ?)",
            (payment.bill_id, payment.amount, payment.paid_date, payment.notes),
        )
        return cur.lastrowid


def update(payment: Payment) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE payments SET bill_id=?, amount=?, paid_date=?, notes=? WHERE id=?",
            (payment.bill_id, payment.amount, payment.paid_date, payment.notes, payment.id),
        )


def delete(payment_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))


def total_paid_by_bill() -> dict[int, Decimal]:
    """Sum of all payments made against each bill, keyed by bill_id.

    Used by the Goals tab to subtract paid contributions from a goal's price.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT bill_id, SUM(amount) AS total FROM payments"
            " WHERE bill_id IS NOT NULL GROUP BY bill_id"
        ).fetchall()
    return {row["bill_id"]: to_decimal(row["total"]) for row in rows}


def latest_paid_dates() -> dict[int, str]:
    """Most recent paid_date per bill, keyed by bill_id.

    Used by the Dashboard to decide whether a carried-over yearly/one-time
    bill's missed cycle has already been paid.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT bill_id, MAX(paid_date) AS latest FROM payments"
            " WHERE bill_id IS NOT NULL GROUP BY bill_id"
        ).fetchall()
    return {row["bill_id"]: row["latest"] for row in rows}


def get_paid_bill_ids_for_month(year: int, month: int) -> set[int]:
    prefix = f"{year}-{month:02d}-"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT bill_id FROM payments"
            " WHERE paid_date LIKE ? AND bill_id IS NOT NULL",
            (prefix + "%",),
        ).fetchall()
    return {row["bill_id"] for row in rows}
