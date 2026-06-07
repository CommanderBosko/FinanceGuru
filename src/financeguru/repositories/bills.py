from financeguru.db import get_connection
from financeguru.models.bill import Bill
from financeguru.money import to_decimal


def get_all() -> list[Bill]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM bills ORDER BY due_day").fetchall()
    return [_row_to_bill(r) for r in rows]


def add(bill: Bill) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO bills (name, amount, due_day, recurrence, is_active, notes)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (bill.name, bill.amount, bill.due_day, bill.recurrence, int(bill.is_active), bill.notes),
        )
        return cur.lastrowid


def update(bill: Bill) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bills SET name=?, amount=?, due_day=?, recurrence=?, is_active=?, notes=?"
            " WHERE id=?",
            (bill.name, bill.amount, bill.due_day, bill.recurrence, int(bill.is_active), bill.notes, bill.id),
        )


def delete(bill_id: int) -> None:
    with get_connection() as conn:
        # New DBs declare the FK with ON DELETE CASCADE, but databases created
        # before that change keep the old constraint, so delete children
        # explicitly to stay correct across both.
        conn.execute("DELETE FROM payments WHERE bill_id=?", (bill_id,))
        conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))


def _row_to_bill(row) -> Bill:
    return Bill(
        id=row["id"],
        name=row["name"],
        amount=to_decimal(row["amount"]),
        due_day=row["due_day"],
        recurrence=row["recurrence"],
        is_active=bool(row["is_active"]),
        notes=row["notes"],
    )
