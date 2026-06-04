from financeguru.db import get_connection
from financeguru.models.payment import Payment


def get_all() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT p.id, p.bill_id, p.amount, p.paid_date, p.notes,
                   b.name AS bill_name
            FROM payments p
            LEFT JOIN bills b ON p.bill_id = b.id
            ORDER BY p.paid_date DESC
        """).fetchall()
    return [dict(r) for r in rows]


def add(payment: Payment) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO payments (bill_id, amount, paid_date, notes) VALUES (?, ?, ?, ?)",
            (payment.bill_id, payment.amount, payment.paid_date, payment.notes),
        )
        return cur.lastrowid


def delete(payment_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM payments WHERE id=?", (payment_id,))


def get_paid_bill_ids_for_month(year: int, month: int) -> set[int]:
    prefix = f"{year}-{month:02d}-"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT bill_id FROM payments"
            " WHERE paid_date LIKE ? AND bill_id IS NOT NULL",
            (prefix + "%",),
        ).fetchall()
    return {row["bill_id"] for row in rows}
