import csv
import sqlite3
from datetime import datetime
from decimal import Decimal

import pytest

import financeguru.db as db
from financeguru.db import _CORE_TABLES, _csv_safe
from financeguru.models.bill import Bill
from financeguru.models.payment import Payment
from financeguru.repositories import bills, payments


def _seed():
    bill_id = bills.add(Bill(name="Power", amount=Decimal("80.00"), due_day=15))
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-06-01", bill_id=bill_id))
    return bill_id


# --- _csv_safe -------------------------------------------------------------

@pytest.mark.parametrize("value", ["=1+1", "+1", "-1", "@cmd", "\tx", "\rx"])
def test_csv_safe_prefixes_formula_triggers(value):
    assert _csv_safe(value) == "'" + value


def test_csv_safe_leaves_ordinary_values_untouched():
    assert _csv_safe("Power") == "Power"
    assert _csv_safe("") == ""
    assert _csv_safe(80.0) == 80.0
    assert _csv_safe(None) is None


# --- backup / restore ------------------------------------------------------

def test_backup_creates_a_readable_copy_with_the_data(tmp_path):
    _seed()
    dest = tmp_path / "backup.db"
    db.backup_database(dest)

    assert dest.exists()
    assert oct(dest.stat().st_mode)[-3:] == "600"
    con = sqlite3.connect(dest)
    try:
        rows = con.execute("SELECT name FROM bills").fetchall()
    finally:
        con.close()
    assert rows == [("Power",)]


def test_restore_replaces_live_data_and_keeps_a_safety_copy(tmp_path):
    _seed()
    backup = tmp_path / "backup.db"
    db.backup_database(backup)

    # Mutate the live database so we can prove the restore reverted it.
    bills.add(Bill(name="Extra", amount=Decimal("5.00"), due_day=1))
    assert len(bills.get_all()) == 2

    db.restore_database(backup)
    names = [b.name for b in bills.get_all()]
    assert names == ["Power"]

    # A timestamped pre-restore safety copy of the prior DB was written.
    safety = list(db.DB_DIR.glob("finance.pre-restore-*.bak"))
    assert len(safety) == 1


def test_restore_rejects_a_non_financeguru_sqlite_file(tmp_path):
    _seed()
    foreign = tmp_path / "foreign.db"
    con = sqlite3.connect(foreign)
    con.execute("CREATE TABLE unrelated (x INTEGER)")
    con.commit()
    con.close()

    with pytest.raises(ValueError, match="not a FinanceGuru backup"):
        db.restore_database(foreign)

    # The live database is untouched.
    assert [b.name for b in bills.get_all()] == ["Power"]


# --- auto_backup -----------------------------------------------------------

def test_auto_backup_writes_dated_owner_only_copy():
    _seed()
    dest = db.auto_backup()

    assert dest is not None
    assert dest.parent == db.DB_DIR / "backups"
    assert dest.name == f"financeguru-auto-{datetime.now():%Y%m%d}.db"
    assert oct(dest.stat().st_mode)[-3:] == "600"
    assert oct(dest.parent.stat().st_mode)[-3:] == "700"
    con = sqlite3.connect(dest)
    try:
        assert con.execute("SELECT name FROM bills").fetchall() == [("Power",)]
    finally:
        con.close()


def test_auto_backup_skips_when_today_already_backed_up():
    _seed()
    first = db.auto_backup()
    assert first is not None
    before = first.read_bytes()

    # New data after the backup must NOT be folded in by a second launch —
    # skip-if-exists is what keeps a post-restore relaunch from clobbering
    # the day's earlier, still-good copy.
    bills.add(Bill(name="Extra", amount=Decimal("5.00"), due_day=1))
    assert db.auto_backup() is None
    assert first.read_bytes() == before


def test_auto_backup_returns_none_without_a_database():
    db.DB_PATH.unlink()
    assert db.auto_backup() is None
    assert not (db.DB_DIR / "backups").exists()


def test_auto_backup_prunes_only_its_own_rotation():
    _seed()
    backups_dir = db.DB_DIR / "backups"
    backups_dir.mkdir()
    # 20 older rotation files plus an unrelated pre-restore safety copy.
    for day in range(1, 21):
        (backups_dir / f"financeguru-auto-202605{day:02d}.db").touch()
    keeper = backups_dir / "finance.pre-restore-20260501-120000.bak"
    keeper.touch()

    db.auto_backup()

    rotation = sorted(p.name for p in backups_dir.glob("financeguru-auto-*.db"))
    assert len(rotation) == db._AUTO_BACKUP_KEEP
    assert rotation[-1] == f"financeguru-auto-{datetime.now():%Y%m%d}.db"
    assert rotation[0] == "financeguru-auto-20260508.db"  # 13 newest of May kept
    assert keeper.exists()


# --- export_all_csv --------------------------------------------------------

def test_export_writes_one_csv_per_table_with_headers(tmp_path):
    _seed()
    out = tmp_path / "export"
    written = db.export_all_csv(out)

    names = {p.name for p in written}
    assert {f"{t}.csv" for t in _CORE_TABLES} <= names
    for path in written:
        assert oct(path.stat().st_mode)[-3:] == "600"

    bills_csv = out / "bills.csv"
    with open(bills_csv, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    assert rows[0][1] == "name"  # header
    assert any("Power" in row for row in rows[1:])


def test_export_neutralizes_formula_injection(tmp_path):
    bills.add(Bill(name="=HYPERLINK(evil)", amount=Decimal("1.00"), due_day=1))
    out = tmp_path / "export"
    db.export_all_csv(out)

    with open(out / "bills.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    name_col = rows[0].index("name")
    exported = [r[name_col] for r in rows[1:]]
    assert "'=HYPERLINK(evil)" in exported


# --- _ensure_column --------------------------------------------------------

def test_ensure_column_is_idempotent_and_validates_identifiers():
    with db.get_connection() as conn:
        # Adding an existing column is a no-op (does not raise).
        db._ensure_column(conn, "incomes", "pay_days", "pay_days TEXT")
        # Unsafe identifiers are rejected before reaching SQL.
        with pytest.raises(ValueError):
            db._ensure_column(conn, "incomes; DROP TABLE bills", "x", "x TEXT")
        with pytest.raises(ValueError):
            db._ensure_column(conn, "incomes", "pay_days", "DROP TABLE bills")


# --- bills.category schema + migration -------------------------------------

def _column_names(conn, table: str) -> set[str]:
    return {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def test_init_db_creates_bills_category_column():
    with db.get_connection() as conn:
        assert "category" in _column_names(conn, "bills")


def test_ensure_column_adds_category_to_a_legacy_bills_table():
    # Drop and recreate a legacy `bills` table lacking the `category` column,
    # writing directly to the fixture's temp DB path.
    con = sqlite3.connect(db.DB_PATH)
    try:
        con.execute("DROP TABLE bills")
        con.execute(
            "CREATE TABLE bills ("
            " id INTEGER PRIMARY KEY,"
            " name TEXT NOT NULL,"
            " amount REAL NOT NULL,"
            " due_day INTEGER NOT NULL,"
            " recurrence TEXT NOT NULL DEFAULT 'monthly',"
            " is_active INTEGER NOT NULL DEFAULT 1,"
            " notes TEXT)"
        )
        con.execute(
            "INSERT INTO bills (name, amount, due_day) VALUES ('Legacy', 12.0, 5)"
        )
        con.commit()
    finally:
        con.close()

    with db.get_connection() as conn:
        assert "category" not in _column_names(conn, "bills")
        db._ensure_column(conn, "bills", "category", "category TEXT NOT NULL DEFAULT 'Other'")
        assert "category" in _column_names(conn, "bills")
        row = conn.execute("SELECT category FROM bills WHERE name='Legacy'").fetchone()
        assert row["category"] == "Other"


# --- expenses core table ---------------------------------------------------

def test_expenses_is_a_core_table():
    assert "expenses" in _CORE_TABLES


def test_export_writes_a_csv_for_the_expenses_table(tmp_path):
    _seed()
    out = tmp_path / "export"
    written = db.export_all_csv(out)
    names = {p.name for p in written}
    assert "expenses.csv" in names
