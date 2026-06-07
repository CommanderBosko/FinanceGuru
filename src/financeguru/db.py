import os
import re
import sqlite3
from decimal import Decimal
from pathlib import Path

_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# Money is handled as Decimal in the app but stored in REAL columns; tell sqlite3
# how to bind a Decimal parameter. Cent-quantized values round-trip exactly.
sqlite3.register_adapter(Decimal, float)

DB_DIR = Path.home() / ".local" / "share" / "financeguru"
DB_PATH = DB_DIR / "finance.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    # Financial data is plaintext SQLite — keep it readable only by the owner,
    # since these machines have multiple local users (bosko, natty).
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_column(conn, table: str, column: str, ddl: str) -> None:
    """Add a column to an existing table if it isn't already present.

    Table/column names and DDL are interpolated directly (SQLite can't bind
    identifiers with ?), so callers MUST pass trusted constants. The identifier
    checks below guard against a future caller accidentally introducing a SQL
    injection sink.
    """
    if not _IDENT_RE.fullmatch(table) or not _IDENT_RE.fullmatch(column):
        raise ValueError(f"unsafe identifier: {table!r}.{column!r}")
    if not ddl.startswith(column + " "):
        raise ValueError(f"ddl must start with the column name: {ddl!r}")
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")


def init_db() -> None:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    # Restrict the data directory to the owner; this also covers the -wal/-journal
    # sidecar files SQLite creates alongside finance.db.
    try:
        os.chmod(DB_DIR, 0o700)
    except OSError:
        pass
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS bills (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                due_day     INTEGER NOT NULL,
                recurrence  TEXT    NOT NULL DEFAULT 'monthly',
                is_active   INTEGER NOT NULL DEFAULT 1,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id     INTEGER REFERENCES bills(id) ON DELETE CASCADE,
                amount      REAL    NOT NULL,
                paid_date   TEXT    NOT NULL,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS stocks (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT    NOT NULL,
                shares          REAL    NOT NULL,
                purchase_price  REAL    NOT NULL,
                purchase_date   TEXT    NOT NULL,
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS incomes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                frequency   TEXT    NOT NULL DEFAULT 'monthly',
                pay_days    TEXT,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS debts (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL,
                balance         REAL    NOT NULL,
                interest_rate   REAL    NOT NULL,
                minimum_payment REAL    NOT NULL,
                notes           TEXT
            );

            CREATE TABLE IF NOT EXISTS goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                price       REAL    NOT NULL,
                target_date TEXT    NOT NULL,
                bill_id     INTEGER REFERENCES bills(id) ON DELETE SET NULL,
                notes       TEXT
            );

            CREATE TABLE IF NOT EXISTS stock_tips (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker          TEXT    NOT NULL,
                action          TEXT    NOT NULL DEFAULT 'Watch',
                target_price    REAL,
                confidence      INTEGER NOT NULL DEFAULT 3,
                notes           TEXT,
                added_date      TEXT    NOT NULL,
                analyst_action  TEXT,
                analyst_target  REAL,
                analyst_count   INTEGER,
                analyst_updated TEXT
            );
        """)

        # Migrations for databases created before a column existed.
        _ensure_column(conn, "incomes", "pay_days", "pay_days TEXT")
