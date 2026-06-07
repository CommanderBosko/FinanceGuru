from financeguru.db import get_connection
from financeguru.models.goal import Goal
from financeguru.money import to_decimal


def _row_to_goal(row) -> Goal:
    return Goal(
        id=row["id"],
        name=row["name"],
        price=to_decimal(row["price"]),
        target_date=row["target_date"],
        notes=row["notes"],
        bill_id=row["bill_id"],
    )


def get_all() -> list[Goal]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM goals ORDER BY target_date").fetchall()
    return [_row_to_goal(r) for r in rows]


def add(goal: Goal) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO goals (name, price, target_date, notes, bill_id)
               VALUES (?, ?, ?, ?, ?)""",
            (goal.name, goal.price, goal.target_date, goal.notes, goal.bill_id),
        )
        return cur.lastrowid or 0


def update(goal: Goal) -> None:
    with get_connection() as conn:
        conn.execute(
            """UPDATE goals SET name=?, price=?, target_date=?, notes=?, bill_id=?
               WHERE id=?""",
            (goal.name, goal.price, goal.target_date, goal.notes, goal.bill_id, goal.id),
        )


def delete(goal_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
