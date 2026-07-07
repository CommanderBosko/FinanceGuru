# Template pattern for a migration test that simulates a pre-migration DB.
#
# The conftest `temp_db` fixture always starts from a fresh init_db(), so it
# never exercises the upgrade path on its own. To test a migration, roll the
# DB back to the OLD shape by hand, tag some rows in that old shape, call
# db.init_db() again (this is the migration running), then assert the new
# shape and that existing records were re-tagged correctly.
#
# Cover both the happy path (migration applies) and the guard (running
# init_db() a second time is a no-op, per the idempotency rule).

def test_rename_migration_renames_and_retags():
    with db.get_connection() as conn:
        conn.execute("UPDATE categories SET name='Food' WHERE name='Groceries'")
    expense_repo.add(Expense(amount=Decimal("40"), spent_date="2026-06-01", category="Food"))
    db.init_db()  # upgrade
    assert "Groceries" in category_repo.names() and "Food" not in category_repo.names()
    assert expense_repo.get_all()[0].category == "Groceries"
