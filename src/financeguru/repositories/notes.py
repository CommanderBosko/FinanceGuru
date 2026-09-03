from financeguru.db import get_connection
from financeguru.models.note import Note


def get_for_month(year: int, month: int) -> list[Note]:
    """Notes filed under ``year``/``month``, newest-first (id as a tiebreak
    for notes added in the same second)."""
    month_year = f"{year:04d}-{month:02d}"
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE month_year=? ORDER BY created_at DESC, id DESC",
            (month_year,),
        ).fetchall()
    return [_row_to_note(r) for r in rows]


def earliest_month() -> str | None:
    """The "YYYY-MM" of the oldest note on file, or None if there are none.

    Used by NotesView to know how far back its month picker needs to reach.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT MIN(month_year) AS earliest FROM notes").fetchone()
    return row["earliest"] if row else None


def get_by_bill_id(bill_id: int) -> list[Note]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM notes WHERE bill_id=?", (bill_id,)).fetchall()
    return [_row_to_note(r) for r in rows]


def get_by_goal_id(goal_id: int) -> list[Note]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM notes WHERE goal_id=?", (goal_id,)).fetchall()
    return [_row_to_note(r) for r in rows]


def add(note: Note) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO notes (month_year, created_at, body, bill_id, goal_id)"
            " VALUES (?, ?, ?, ?, ?)",
            (note.month_year, note.created_at, note.body, note.bill_id, note.goal_id),
        )
        return cur.lastrowid or 0


def update(note: Note) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE notes SET month_year=?, body=?, bill_id=?, goal_id=? WHERE id=?",
            (note.month_year, note.body, note.bill_id, note.goal_id, note.id),
        )


def delete(note_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE id=?", (note_id,))


def delete_for_bill(bill_id: int) -> None:
    """Delete every note linked to ``bill_id``.

    Used when the user chooses "delete the linked notes too" while deleting a
    Bill; if they decline, the notes stay and the FK's ON DELETE SET NULL
    clears their link when the Bill row is removed instead.
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE bill_id=?", (bill_id,))


def delete_for_goal(goal_id: int) -> None:
    """Delete every note linked to ``goal_id`` (see ``delete_for_bill``)."""
    with get_connection() as conn:
        conn.execute("DELETE FROM notes WHERE goal_id=?", (goal_id,))


def _row_to_note(row) -> Note:
    return Note(
        id=row["id"],
        month_year=row["month_year"],
        created_at=row["created_at"],
        body=row["body"],
        bill_id=row["bill_id"],
        goal_id=row["goal_id"],
    )
