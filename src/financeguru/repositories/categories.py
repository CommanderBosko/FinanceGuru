"""DB access for the user-managed ``categories`` table.

The pickers (bill/expense dialogs) and the charts read the live list through
here so a category the user adds shows up everywhere without a restart. The
table is seeded by ``db.init_db()``; see ``financeguru.categories`` for the
seed list and the protected-category rules.
"""

from financeguru.db import get_connection
from financeguru.models.category import Category


def get_all() -> list[Category]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM categories ORDER BY position, name"
        ).fetchall()
    return [_row_to_category(r) for r in rows]


def names() -> list[str]:
    """The category names in display order — for combo boxes and chart ordering."""
    return [c.name for c in get_all()]


def add(name: str) -> int | None:
    """Append a new user category. Raises sqlite3.IntegrityError on a duplicate
    name (the UNIQUE constraint); callers validate first and surface the error."""
    name = name.strip()
    with get_connection() as conn:
        position = conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM categories"
        ).fetchone()[0]
        cur = conn.execute(
            "INSERT INTO categories (name, position, is_protected)"
            " VALUES (?, ?, 0)",
            (name, position),
        )
        return cur.lastrowid


def rename(category_id: int, new_name: str) -> None:
    """Rename a category. The ``is_protected=0`` guard means protected
    categories silently cannot be renamed even if a caller tries."""
    with get_connection() as conn:
        conn.execute(
            "UPDATE categories SET name=? WHERE id=? AND is_protected=0",
            (new_name.strip(), category_id),
        )


def delete(category_id: int) -> None:
    """Delete a category from the picker. Existing bills/expenses tagged with it
    keep their text value. Protected categories cannot be deleted."""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM categories WHERE id=? AND is_protected=0",
            (category_id,),
        )


def _row_to_category(row) -> Category:
    return Category(
        id=row["id"],
        name=row["name"],
        position=row["position"],
        is_protected=bool(row["is_protected"]),
    )
