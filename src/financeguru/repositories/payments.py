from financeguru.db import get_connection
from financeguru.models.payment import Payment


def add(payment: Payment) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO payments (bill_id, amount, paid_date, notes) VALUES (?, ?, ?, ?)",
            (payment.bill_id, payment.amount, payment.paid_date, payment.notes),
        )
        return cur.lastrowid
