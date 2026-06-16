from financeguru.db import get_connection
from financeguru.models.expense import Expense
from financeguru.money import to_decimal


def get_all() -> list[Expense]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM expenses ORDER BY spent_date DESC"
        ).fetchall()
    return [_row_to_expense(r) for r in rows]


def add(expense: Expense) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO expenses (amount, spent_date, category, notes)"
            " VALUES (?, ?, ?, ?)",
            (expense.amount, expense.spent_date, expense.category, expense.notes),
        )
        return cur.lastrowid


def update(expense: Expense) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE expenses SET amount=?, spent_date=?, category=?, notes=?"
            " WHERE id=?",
            (expense.amount, expense.spent_date, expense.category, expense.notes, expense.id),
        )


def delete(expense_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM expenses WHERE id=?", (expense_id,))


def _row_to_expense(row) -> Expense:
    return Expense(
        id=row["id"],
        amount=to_decimal(row["amount"]),
        spent_date=row["spent_date"],
        category=row["category"],
        notes=row["notes"],
    )
