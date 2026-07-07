---
name: db-migration
description: Make a schema change to FinanceGuru's SQLite database the safe, repeatable way — update init_db(), write a guarded idempotent migration for existing databases, get the ordering vs seeding right, re-tag free-text records, and prove it with a migration test plus qt-smoke. Use when the user says "db-migration", "migrate the schema", "add a column", "add a table", "rename a category", "change the database schema", or "handle existing databases for this change".
---

# DB Migration

Change the schema in `src/financeguru/db.py` so that **both a fresh database and every already-populated one** end up correct after the app next starts. FinanceGuru has no migration framework: `init_db()` runs on every launch and is the one place that creates tables, backfills columns, applies one-time data fixups, and seeds defaults. Get the steps and their *order* right and the change is safe; get them wrong and you either crash on an existing DB or silently double up data.

This skill encodes the conventions that aren't obvious from reading the code once. Pair it with `qt-smoke` (prove the UI reflects the change) and `audit` (for larger changes).

## Background: how init_db() is structured

`init_db()` runs these phases **in this order**, and order matters:

1. `executescript(...)` — `CREATE TABLE IF NOT EXISTS` for every table. Safe to re-run; never alters an existing table.
2. `_ensure_column(conn, table, column, ddl)` calls — additive column backfills for older DBs (SQLite can't bind identifiers, so this helper validates the table/column names first).
3. One-time data migrations (e.g. `_rename_category`) — renames/fixups on existing rows.
4. Seeding loops (e.g. categories) — `INSERT OR IGNORE` the canonical defaults.

Other invariants to respect:
- `get_connection()` enables `PRAGMA foreign_keys = ON` per connection and sets `row_factory = sqlite3.Row`.
- Money is stored in `REAL` columns; a `Decimal` adapter binds it (`sqlite3.register_adapter(Decimal, float)`). New money columns are `REAL NOT NULL DEFAULT ...`.
- Category columns on `bills`/`expenses` are **free text, not foreign keys**. Deleting/renaming a category does not cascade — you must re-tag rows yourself if you want existing records updated.
- `_CORE_TABLES` is the set restore validation requires. **Do not add a newly-seeded table to it** — `restore_database()` re-runs `init_db()` at the end, so an older backup that lacks the new table is still valid and will gain it. Adding it to `_CORE_TABLES` would wrongly reject good backups.

## Steps

1. **Classify the change.** Pick the phase(s) you need:
   - **New table** → add a `CREATE TABLE IF NOT EXISTS` block to the `executescript`. If it carries defaults, add a seeding loop (step 4). Do **not** touch `_CORE_TABLES`.
   - **New column** → add it to the table's `CREATE TABLE` block (for fresh DBs) **and** an `_ensure_column(conn, table, "col", "col TYPE ...")` call (for existing DBs). The DDL string must start with the column name — the helper enforces this.
   - **Rename / data fixup** → add a guarded one-time migration helper (step 3), called **before** any seeding loop it interacts with.
   - **Seed/default rows** → an `INSERT OR IGNORE` loop keyed on a `UNIQUE` column (step 4).

2. **Keep migrations idempotent.** `init_db()` runs on every launch, so every migration must be a no-op once applied. Use `IF NOT EXISTS`, `INSERT OR IGNORE`, `_ensure_column`'s presence check, or an explicit guard that reads current state first. Never write a migration that fails or duplicates on a second run.

3. **For a data rename/fixup, write a guarded helper and re-tag records.** Mirror `_rename_category`: read current state, bail if the change is already applied *or* would collide, then update the row **and** re-tag every free-text reference. Read `assets/rename_category_template.py` for the pattern and adapt it — swap the table/column names and add an `UPDATE` line for every free-text table that references the old value. Decide deliberately whether to re-tag existing records (a *complete* rename) or leave them (the in-app picker rename is deliberately picker-only). State which you chose and why in a comment.

4. **Order data migrations BEFORE seeding.** A rename must run before the `INSERT OR IGNORE` seeding loop, or the loop re-adds the old name as a brand-new row. On a fresh DB the table is still empty at migration time, so a well-guarded migration correctly no-ops and seeding inserts the new names directly. Verify both paths in your head before moving on.

5. **Update the single source of truth, not just the DB.** Category names live in `src/financeguru/categories.py` (`CATEGORIES`, `PROTECTED_CATEGORIES`); the dialogs and charts read the live list from `repositories/categories.py`. If your change touches a constant or seed list, update it there and fix any docstring/example/test that hard-codes the old value (e.g. reporting docstrings, `test_categories.py`).

6. **Write a migration test that simulates a pre-migration DB.** The `temp_db` conftest fixture calls a fresh `init_db()`, so to exercise the *upgrade* path you must roll the DB back to the old shape, tag some rows, then call `db.init_db()` again and assert. Cover the happy path **and** the guard (e.g. the no-clobber case). Read `assets/migration_test_template.py` for the pattern and adapt it to the change under test.

7. **Run the suite and a smoke test.**
   ```bash
   nix develop --command python -m pytest -q
   ```
   Then `qt-smoke` the views/dialogs that read the changed data (e.g. a picker now shows the new names, a new column round-trips through a dialog). Both must pass before you call it done.

8. **Report.** State what schema changed, how fresh vs existing DBs each end up correct, whether existing records were re-tagged, and the test/smoke results. Note that the migration takes effect on the user's machine the next time the app starts (since `init_db()` runs at launch).

## Gotchas

- **Migrations run on every launch** — non-idempotent ones corrupt or duplicate on the second start. This is the most common mistake.
- **Order is load-bearing**: data fixups before seeding loops, always.
- **Don't add seeded tables to `_CORE_TABLES`** — it makes `restore_database()` reject valid older backups.
- **Category columns are free text** — renaming/deleting a category does not cascade; re-tag rows yourself if you want existing data updated.
- **`_ensure_column` DDL must start with the column name** and use a plain-identifier table/column, or it raises by design.
- **The conftest `temp_db` fixture always starts fresh** — it does not exercise the upgrade path. You must simulate the old shape yourself to test a migration.
- **Schema work itself belongs in `nix develop`** — `pytest` and any `python` invocation need the dev shell; PySide6/LSP import errors outside it are expected, not real.
