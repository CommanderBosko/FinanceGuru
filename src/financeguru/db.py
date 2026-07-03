import csv
import os
import re
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator

from financeguru.categories import CATEGORIES, PROTECTED_CATEGORIES


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

# The tables every FinanceGuru database must have. Used to reject a restore from
# an unrelated SQLite file before it overwrites the live data.
_CORE_TABLES = {
    "bills", "payments", "stocks", "incomes", "debts", "goals", "stock_tips",
    "expenses",
}

# A cell whose first character is one of these is interpreted as a formula by
# Excel / LibreOffice Calc when the CSV is opened. Prefixing with a literal
# apostrophe neutralises the formula while preserving the displayed value.
_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def _csv_safe(value):
    """Defuse spreadsheet formula injection in an exported cell value."""
    if isinstance(value, str) and value and value[0] in _CSV_FORMULA_PREFIXES:
        return "'" + value
    return value

# Money is handled as Decimal in the app but stored in REAL columns; tell sqlite3
# how to bind a Decimal parameter. Cent-quantized values round-trip exactly.
sqlite3.register_adapter(Decimal, float)

DB_DIR = Path.home() / ".local" / "share" / "financeguru"
DB_PATH = DB_DIR / "finance.db"


@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Yield a configured connection inside a transaction, then close it.

    ``with conn`` commits on success / rolls back on error but never *closes* the
    connection; wrapping it here guarantees the handle (and its file descriptor)
    is released deterministically rather than waiting on GC.
    """
    conn = sqlite3.connect(DB_PATH)
    # Financial data is plaintext SQLite — keep it readable only by the owner,
    # since these machines have multiple local users (bosko, natty).
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


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


# One-time renames of seeded categories, applied to existing databases on
# startup. Each (old, new) renames the `categories` row and re-tags any bills
# and expenses still carrying the old name, so the rename is complete rather
# than leaving the old text on historical records.
_CATEGORY_RENAMES = [
    ("Food", "Groceries"),
    ("Eating out", "Restaurants"),
]


def _rename_category(conn, old: str, new: str) -> None:
    """Rename a category and re-tag the records that reference it.

    Guarded so it is a no-op once applied, on a fresh (not-yet-seeded) database,
    or if the user already has a category with the new name — in which case the
    old one is left alone rather than clobbered.
    """
    names = {row["name"] for row in conn.execute("SELECT name FROM categories")}
    if old not in names or new in names:
        return
    conn.execute("UPDATE categories SET name=? WHERE name=?", (new, old))
    conn.execute("UPDATE bills SET category=? WHERE category=?", (new, old))
    conn.execute("UPDATE expenses SET category=? WHERE category=?", (new, old))


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
                due_month   INTEGER,
                due_year    INTEGER,
                recurrence  TEXT    NOT NULL DEFAULT 'monthly',
                is_active   INTEGER NOT NULL DEFAULT 1,
                notes       TEXT,
                category    TEXT    NOT NULL DEFAULT 'Other'
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

            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                amount      REAL    NOT NULL,
                spent_date  TEXT    NOT NULL,
                category    TEXT    NOT NULL DEFAULT 'Other',
                notes       TEXT
            );

            -- Daily "tracked net worth" history: stock value − debt balances +
            -- cumulative goal contributions (cash/bank isn't tracked anywhere).
            -- One row per calendar day, upserted on launch and after each price
            -- refresh; accrues so the future trend chart has data to plot.
            -- Deliberately NOT in _CORE_TABLES: that set is the identity check
            -- for restores, and adding to it would reject older, perfectly
            -- valid backups (init_db() after restore creates this table).
            CREATE TABLE IF NOT EXISTS snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                snap_date    TEXT    NOT NULL UNIQUE,
                stock_value  REAL    NOT NULL,
                debt_total   REAL    NOT NULL,
                goal_savings REAL    NOT NULL,
                net_worth    REAL    NOT NULL
            );

            -- User-managed spending categories. Bills/expenses store their
            -- category as free text (not a foreign key), so deleting a category
            -- here only removes it from the pickers; existing rows keep their
            -- value. Seeded from financeguru.categories.CATEGORIES below.
            CREATE TABLE IF NOT EXISTS categories (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                name         TEXT    NOT NULL UNIQUE,
                position     INTEGER NOT NULL DEFAULT 0,
                is_protected INTEGER NOT NULL DEFAULT 0
            );
        """)

        # Migrations for databases created before a column existed.
        _ensure_column(conn, "incomes", "pay_days", "pay_days TEXT")
        _ensure_column(conn, "bills", "category", "category TEXT NOT NULL DEFAULT 'Other'")
        _ensure_column(conn, "bills", "due_month", "due_month INTEGER")
        _ensure_column(conn, "bills", "due_year", "due_year INTEGER")
        _ensure_column(conn, "stocks", "last_price", "last_price REAL")
        _ensure_column(conn, "stocks", "last_price_date", "last_price_date TEXT")

        # Apply category renames before seeding so the new name is already
        # present and the INSERT OR IGNORE below doesn't re-add the old one.
        for old, new in _CATEGORY_RENAMES:
            _rename_category(conn, old, new)

        # Seed the canonical categories. INSERT OR IGNORE keys on the UNIQUE
        # name, so this is idempotent and never disturbs user-added rows or a
        # category whose position the user has changed — it only backfills any
        # canonical name that is missing (including on an older restored DB).
        for position, name in enumerate(CATEGORIES):
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, position, is_protected)"
                " VALUES (?, ?, ?)",
                (name, position, 1 if name in PROTECTED_CATEGORIES else 0),
            )


def backup_database(dest: Path) -> None:
    """Write a consistent copy of the database to ``dest``.

    Uses SQLite's online backup API so the copy is transactionally consistent
    even if a WAL sidecar holds uncommitted-to-main pages.
    """
    dest = Path(dest)
    # Lock the destination down *before* sqlite writes financial data into it, so
    # the backup is never momentarily world-readable on these multi-user machines.
    dest.touch(exist_ok=True)
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass
    with get_connection() as src, sqlite3.connect(dest) as dst:
        src.backup(dst)
    try:
        os.chmod(dest, 0o600)
    except OSError:
        pass


_AUTO_BACKUP_KEEP = 14
_AUTO_BACKUP_GLOB = "financeguru-auto-*.db"


def auto_backup() -> Path | None:
    """Silent daily rotating backup, run at every launch.

    Called before ``init_db()`` so the copy captures the pre-migration
    database — if a new release ships a bad migration, today's backup still
    holds the untouched data. Skip-if-exists rather than overwrite, so
    relaunching after a restore can't clobber the day's earlier, still-good
    copy. Pruning only ever touches this function's own rotation
    (``financeguru-auto-*.db``); restore's ``.pre-restore-*.bak`` safety
    copies are never candidates. Returns the path written, or None when
    there is no database yet or today's backup already exists.
    """
    if not DB_PATH.exists():
        return None
    backups_dir = DB_DIR / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(backups_dir, 0o700)
    except OSError:
        pass
    dest = backups_dir / f"financeguru-auto-{datetime.now():%Y%m%d}.db"
    if dest.exists():
        return None
    backup_database(dest)
    # The date-stamped names sort chronologically, so newest-first is a
    # plain reverse sort; everything past the keep window is dropped.
    rotation = sorted(backups_dir.glob(_AUTO_BACKUP_GLOB), reverse=True)
    for stale in rotation[_AUTO_BACKUP_KEEP:]:
        stale.unlink(missing_ok=True)
    return dest


def restore_database(src: Path) -> None:
    """Replace the live database with the backup at ``src``.

    Validates that ``src`` is a genuine FinanceGuru database before overwriting,
    keeps a timestamped safety copy of the current data so the operation is
    recoverable, clears stale -wal/-shm/-journal sidecars that would otherwise
    corrupt the restored file, and re-runs migrations so a backup from an older
    app version gains any columns added since.
    """
    src = Path(src)
    # Probe: confirm it's a SQLite file AND that it carries our schema, so an
    # unrelated DB is rejected with a clear error instead of silently wiping data.
    with sqlite3.connect(src) as probe:
        names = {
            row[0]
            for row in probe.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    missing = _CORE_TABLES - names
    if missing:
        raise ValueError(
            "This file is not a FinanceGuru backup "
            f"(missing tables: {', '.join(sorted(missing))})."
        )

    # Safety copy of the current DB before we overwrite it.
    if DB_PATH.exists():
        safety = DB_PATH.with_name(
            f"{DB_PATH.stem}.pre-restore-{datetime.now():%Y%m%d-%H%M%S}.bak"
        )
        shutil.copyfile(DB_PATH, safety)
        try:
            os.chmod(safety, 0o600)
        except OSError:
            pass

    shutil.copyfile(src, DB_PATH)
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = DB_PATH.with_name(DB_PATH.name + suffix)
        sidecar.unlink(missing_ok=True)
    try:
        os.chmod(DB_PATH, 0o600)
    except OSError:
        pass
    # Apply any migrations the restored (possibly older) schema is missing.
    init_db()


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
            # The table name is interpolated into SQL and the filename; only
            # plain identifiers are safe. Names from sqlite_master are normally
            # fine, but a restored/crafted DB could carry one with quotes, "/",
            # or ".." — skip those rather than build an injectable query or write
            # outside the chosen folder.
            if not _IDENT_RE.fullmatch(table):
                continue
            cur = conn.execute(f'SELECT * FROM "{table}"')
            path = dest_dir / f"{table}.csv"
            # The CSV holds the same plaintext financial data as the DB. Create it
            # owner-only *before* writing so it's never momentarily world-readable
            # on these multi-user machines (open(path,"w") would use the umask).
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with open(fd, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([_csv_safe(col[0]) for col in cur.description])
                writer.writerows(
                    [_csv_safe(value) for value in row] for row in cur.fetchall()
                )
            # O_CREAT leaves an already-existing file's mode untouched; re-assert.
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            written.append(path)
    return written
