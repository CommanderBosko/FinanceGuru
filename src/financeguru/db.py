import csv
import os
import re
import shutil
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


def backup_database(dest: Path) -> None:
    """Write a consistent copy of the database to ``dest``.

    Uses SQLite's online backup API so the copy is transactionally consistent
    even if a WAL sidecar holds uncommitted-to-main pages.
    """
    dest = Path(dest)
    with get_connection() as src, sqlite3.connect(dest) as dst:
        src.backup(dst)
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass


def restore_database(src: Path) -> None:
    """Replace the live database with the backup at ``src``.

    Validates that ``src`` is a readable SQLite database before overwriting, and
    clears any stale -wal/-shm/-journal sidecars that would otherwise be applied
    on top of the freshly restored file and corrupt it.
    """
    src = Path(src)
    # Probe: opening + reading the schema fails loudly on a non-SQLite file.
    with sqlite3.connect(src) as probe:
        probe.execute("SELECT count(*) FROM sqlite_master").fetchone()
    shutil.copyfile(src, DB_PATH)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = DB_PATH.with_name(DB_PATH.name + suffix)
        sidecar.unlink(missing_ok=True)
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass


def export_all_csv(dest_dir: Path) -> list[Path]:
    """Export every user table to ``dest_dir`` as one CSV file per table.

    Returns the list of files written.
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with get_connection() as conn:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
                "ORDER BY name"
            )
        ]
        for table in tables:
            cur = conn.execute(f"SELECT * FROM {table}")
            path = dest_dir / f"{table}.csv"
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([col[0] for col in cur.description])
                writer.writerows(cur.fetchall())
            written.append(path)
    return written
