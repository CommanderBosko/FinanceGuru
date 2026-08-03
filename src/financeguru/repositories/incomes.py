from financeguru.db import get_connection
from financeguru.models.income import Income
from financeguru.money import to_decimal


def _row_to_income(row) -> Income:
    return Income(
        id=row["id"],
        name=row["name"],
        amount=to_decimal(row["amount"]),
        pay_day=row["pay_day"],
        notes=row["notes"],
    )


def get_all() -> list[Income]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM incomes ORDER BY name").fetchall()
    return [_row_to_income(r) for r in rows]


def add(income: Income) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO incomes (name, amount, pay_day, notes) VALUES (?, ?, ?, ?)",
            (income.name, income.amount, income.pay_day, income.notes),
        )
        return cur.lastrowid or 0


def update(income: Income) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE incomes SET name=?, amount=?, pay_day=?, notes=? WHERE id=?",
            (income.name, income.amount, income.pay_day, income.notes, income.id),
        )


def delete(income_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM incomes WHERE id=?", (income_id,))
