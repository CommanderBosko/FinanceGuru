"""Generic key/value settings store — see the `preferences` table in db.py.

Not currency-specific: any feature that needs to remember a small bit of state
across restarts (a picker's last selection, a toggle) can reuse this rather
than adding another single-purpose table.
"""

from financeguru.db import get_connection


def get(key: str, default: str | None = None) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM preferences WHERE key=?", (key,)
        ).fetchone()
    return row["value"] if row is not None else default


def set(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO preferences (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def set_many(items: dict[str, str]) -> None:
    """Upsert several key/value pairs in one connection/transaction.

    A caller writing several related keys at once (e.g. a form's from/to/
    amount on every change) would otherwise open one connection per key via
    set() — wasteful on a UI-input hot path where this fires on every
    keystroke or combo change.
    """
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO preferences (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            list(items.items()),
        )
