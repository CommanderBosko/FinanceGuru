from financeguru.db import get_connection
from financeguru.models.debt import Debt


def _row_to_debt(row) -> Debt:
    return Debt(
        id=row["id"],
        name=row["name"],
        balance=row["balance"],
        interest_rate=row["interest_rate"],
        minimum_payment=row["minimum_payment"],
        notes=row["notes"],
    )


def get_all() -> list[Debt]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM debts ORDER BY balance DESC"
        ).fetchall()
    return [_row_to_debt(r) for r in rows]


def add(debt: Debt) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO debts (name, balance, interest_rate, minimum_payment, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (debt.name, debt.balance, debt.interest_rate, debt.minimum_payment, debt.notes),
        )
        return cur.lastrowid or 0


def update(debt: Debt) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE debts SET name=?, balance=?, interest_rate=?, minimum_payment=?, notes=?
               WHERE id=?""",
            (debt.name, debt.balance, debt.interest_rate, debt.minimum_payment, debt.notes, debt.id),
        )


def delete(debt_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM debts WHERE id=?", (debt_id,))
