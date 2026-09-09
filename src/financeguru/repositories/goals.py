import sqlite3

from financeguru.db import get_connection
from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.money import to_decimal
from financeguru.repositories import bills


def _row_to_goal(row) -> Goal:
    return Goal(
        id=row["id"],
        name=row["name"],
        price=to_decimal(row["price"]),
        target_date=row["target_date"],
        start_date=row["start_date"],
        notes=row["notes"],
        bill_id=row["bill_id"],
    )


def get_all() -> list[Goal]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM goals ORDER BY target_date").fetchall()
    return [_row_to_goal(r) for r in rows]


def add(goal: Goal, conn: sqlite3.Connection | None = None) -> int:
    """Insert `goal`, returning its new id.

    Pass an existing `conn` to run inside a caller-owned transaction instead
    of opening (and committing) a new one — see `add_with_bill`.
    """
    if conn is not None:
        cur = conn.execute(
            """INSERT INTO goals (name, price, target_date, start_date, notes, bill_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (goal.name, goal.price, goal.target_date, goal.start_date, goal.notes, goal.bill_id),
        )
        return cur.lastrowid or 0
    with get_connection() as conn:
        return add(goal, conn=conn)


def update(goal: Goal, conn: sqlite3.Connection | None = None) -> None:
    """Update `goal`. Pass an existing `conn` to join a caller-owned transaction."""
    if conn is not None:
        conn.execute(
            """UPDATE goals SET name=?, price=?, target_date=?, start_date=?, notes=?, bill_id=?
               WHERE id=?""",
            (goal.name, goal.price, goal.target_date, goal.start_date, goal.notes, goal.bill_id,
             goal.id),
        )
        return
    with get_connection() as conn:
        update(goal, conn=conn)


def delete(
    goal_id: int,
    delete_linked_notes: bool = False,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Delete a goal, optionally its linked notes too, in one transaction.

    ``delete_linked_notes=True`` also deletes any notes linked to this goal
    (the caller — GoalsView's delete-cascade prompt — has already asked the
    user). Left False (the default), a linked note survives with its link
    cleared by the ``notes.goal_id`` FK's ON DELETE SET NULL.

    Pass an existing `conn` to run inside a caller-owned transaction instead
    of opening a new one — see `delete_with_bill`.
    """
    if conn is not None:
        if delete_linked_notes:
            conn.execute("DELETE FROM notes WHERE goal_id=?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
        return
    with get_connection() as conn:
        delete(goal_id, delete_linked_notes=delete_linked_notes, conn=conn)


# ── Atomic goal+bill operations ─────────────────────────────────────────────
# A Goal's mirrored Bill (see GoalsView._bill_for_goal) is a second row in a
# different table that must rise and fall with the Goal. Doing that as two
# separate get_connection() calls (each its own transaction) means a failure
# between them — a full disk, a mid-write crash — can leave a phantom
# ownerless Bill (add/edit) or an orphaned Goal that silently lost its whole
# funding history (delete: the bill and its payments are already gone, but
# the goal survives). These three wrap both writes in one transaction so
# that can't happen.

def add_with_bill(goal: Goal, bill: Bill) -> tuple[int, int]:
    """Insert `goal` and its mirrored `bill` together, atomically.

    Sets `goal.bill_id` from the new bill's id before inserting the goal.
    Returns (goal_id, bill_id).
    """
    with get_connection() as conn:
        bill_id = bills.add(bill, conn=conn)
        goal.bill_id = bill_id
        goal_id = add(goal, conn=conn)
    return goal_id, bill_id


def update_with_bill(goal: Goal, bill: Bill, *, bill_is_new: bool) -> None:
    """Update `goal` and its mirrored `bill` together, atomically.

    Pass `bill_is_new=True` when `goal.bill_id` is None (its mirrored bill
    doesn't exist yet — e.g. a pre-Goals-feature row, or one whose bill was
    separately deleted) so the bill is inserted rather than updated, and
    `goal.bill_id` is set from the new id before the goal itself is written.
    """
    with get_connection() as conn:
        if bill_is_new:
            goal.bill_id = bills.add(bill, conn=conn)
        else:
            bills.update(bill, conn=conn)
        update(goal, conn=conn)


def delete_with_bill(goal_id: int, bill_id: int | None, delete_linked_notes: bool = False) -> None:
    """Delete `goal` and its mirrored bill (if any) together, atomically.

    Mirrors `delete`'s / `bills.delete`'s `delete_linked_notes` semantics for
    both linked-note sets (via goal_id and via bill_id) so a caller that
    already resolved the "delete linked notes too?" prompt across both can
    pass one flag.
    """
    with get_connection() as conn:
        if bill_id is not None:
            bills.delete(bill_id, delete_linked_notes=delete_linked_notes, conn=conn)
        if delete_linked_notes:
            conn.execute("DELETE FROM notes WHERE goal_id=?", (goal_id,))
        conn.execute("DELETE FROM goals WHERE id=?", (goal_id,))
