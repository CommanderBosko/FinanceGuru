import sqlite3
from decimal import Decimal

import pytest

import financeguru.db as db
from financeguru.categories import CATEGORIES, DEFAULT_CATEGORY, SAVINGS_CATEGORY
from financeguru.models.bill import Bill
from financeguru.models.expense import Expense
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import categories as category_repo
from financeguru.repositories import expenses as expense_repo


def test_init_db_seeds_canonical_categories_in_order():
    assert category_repo.names() == CATEGORIES


def test_rename_migration_renames_category_and_retags_records():
    # Simulate a pre-rename database: roll the seeded names back to the old ones
    # and tag a bill and an expense with them, the way an existing DB would be.
    with db.get_connection() as conn:
        conn.execute("UPDATE categories SET name='Food' WHERE name='Groceries'")
        conn.execute("UPDATE categories SET name='Eating out' WHERE name='Restaurants'")
    bid = bill_repo.add(Bill(name="Lunch", amount=Decimal("9"), due_day=1, category="Eating out"))
    expense_repo.add(Expense(amount=Decimal("40"), spent_date="2026-06-01", category="Food"))

    db.init_db()  # re-run: the migration renames and re-tags

    names = category_repo.names()
    assert "Groceries" in names and "Food" not in names
    assert "Restaurants" in names and "Eating out" not in names
    assert next(b for b in bill_repo.get_all() if b.id == bid).category == "Restaurants"
    assert expense_repo.get_all()[0].category == "Groceries"


def test_rename_migration_does_not_clobber_an_existing_new_name():
    # If the user already made a "Groceries" category, the old "Food" is left
    # alone rather than triggering a UNIQUE collision.
    with db.get_connection() as conn:
        conn.execute("UPDATE categories SET name='Food' WHERE name='Groceries'")
    category_repo.add("Groceries")

    db.init_db()  # must be a no-op for this pair, not raise

    names = category_repo.names()
    assert "Groceries" in names and "Food" in names


def test_savings_and_other_are_protected():
    by_name = {c.name: c for c in category_repo.get_all()}
    assert by_name[SAVINGS_CATEGORY].is_protected
    assert by_name[DEFAULT_CATEGORY].is_protected
    assert not by_name["Groceries"].is_protected


def test_seeding_is_idempotent():
    import financeguru.db as db

    db.init_db()  # run again on the already-seeded temp DB
    assert category_repo.names() == CATEGORIES


def test_add_appends_after_seeded_categories():
    category_repo.add("Childcare")
    assert category_repo.names()[-1] == "Childcare"


def test_add_duplicate_name_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError):
        category_repo.add("Groceries")


def test_rename_user_category():
    cid = category_repo.add("Gifts")
    category_repo.rename(cid, "Presents")
    assert "Presents" in category_repo.names()
    assert "Gifts" not in category_repo.names()


def test_rename_protected_category_is_a_no_op():
    other = next(c for c in category_repo.get_all() if c.name == DEFAULT_CATEGORY)
    category_repo.rename(other.id, "Misc")
    assert DEFAULT_CATEGORY in category_repo.names()
    assert "Misc" not in category_repo.names()


def test_delete_user_category():
    cid = category_repo.add("Hobbies")
    category_repo.delete(cid)
    assert "Hobbies" not in category_repo.names()


def test_delete_protected_category_is_a_no_op():
    savings = next(c for c in category_repo.get_all() if c.name == SAVINGS_CATEGORY)
    category_repo.delete(savings.id)
    assert SAVINGS_CATEGORY in category_repo.names()
