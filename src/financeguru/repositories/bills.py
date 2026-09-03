from datetime import date

from financeguru.db import get_connection
from financeguru.models.bill import Bill
from financeguru.money import to_decimal


def get_all(today: date | None = None) -> list[Bill]:
    """All bills in chronological "next due" order, relative to ``today``.

    A plain ``ORDER BY due_day`` interleaves monthly bills with yearly/
    one-time ones in a way that ignores how far off their due_month/due_year
    actually is, so the ordering is computed in Python via
    ``Bill.due_sort_key`` instead (see that method for the exact rules).
    ``today`` defaults to the real current date; tests pass a fixed one for
    determinism.
    """
    today = today or date.today()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM bills ORDER BY id").fetchall()
    result = [_row_to_bill(r) for r in rows]
    result.sort(key=lambda b: b.due_sort_key(today))
    return result


def add(bill: Bill) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO bills"
            " (name, amount, due_day, due_month, due_year, recurrence, is_active, notes, category)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (bill.name, bill.amount, bill.due_day, bill.due_month, bill.due_year,
             bill.recurrence, int(bill.is_active), bill.notes, bill.category),
        )
        return cur.lastrowid or 0


def update(bill: Bill) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE bills SET name=?, amount=?, due_day=?, due_month=?, due_year=?, recurrence=?,"
            " is_active=?, notes=?, category=? WHERE id=?",
            (bill.name, bill.amount, bill.due_day, bill.due_month, bill.due_year,
             bill.recurrence, int(bill.is_active), bill.notes, bill.category, bill.id),
        )


def delete(bill_id: int, delete_linked_notes: bool = False) -> None:
    """Delete a bill and its payments in one transaction.

    ``delete_linked_notes=True`` also deletes any notes linked to this bill in
    the same transaction (the caller — BillsView's delete-cascade prompt —
    has already asked the user). Left False (the default, and every other
    call site), a linked note survives with its link cleared by the
    ``notes.bill_id`` FK's ON DELETE SET NULL once the bill row is gone.
    """
    with get_connection() as conn:
        # New DBs declare the FK with ON DELETE CASCADE, but databases created
        # before that change keep the old constraint, so delete children
        # explicitly to stay correct across both.
        conn.execute("DELETE FROM payments WHERE bill_id=?", (bill_id,))
        if delete_linked_notes:
            conn.execute("DELETE FROM notes WHERE bill_id=?", (bill_id,))
        conn.execute("DELETE FROM bills WHERE id=?", (bill_id,))


def _row_to_bill(row) -> Bill:
    return Bill(
        id=row["id"],
        name=row["name"],
        amount=to_decimal(row["amount"]),
        due_day=row["due_day"],
        due_month=row["due_month"],
        due_year=row["due_year"],
        recurrence=row["recurrence"],
        is_active=bool(row["is_active"]),
        notes=row["notes"],
        category=row["category"],
    )
