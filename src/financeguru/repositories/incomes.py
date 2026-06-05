from financeguru.db import get_connection
from financeguru.models.income import Income


def _row_to_income(row) -> Income:
    return Income(
        id=row["id"],
        name=row["name"],
        amount=row["amount"],
        frequency=row["frequency"],
        notes=row["notes"],
    )


def get_all() -> list[Income]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM incomes ORDER BY name").fetchall()
    return [_row_to_income(r) for r in rows]


def add(income: Income) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO incomes (name, amount, frequency, notes) VALUES (?, ?, ?, ?)",
            (income.name, income.amount, income.frequency, income.notes),
        )
        return cur.lastrowid or 0


def update(income: Income) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE incomes SET name=?, amount=?, frequency=?, notes=? WHERE id=?",
            (income.name, income.amount, income.frequency, income.notes, income.id),
        )


def delete(income_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM incomes WHERE id=?", (income_id,))
