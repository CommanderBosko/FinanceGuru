import sqlite3

import pytest

from financeguru.categories import CATEGORIES, DEFAULT_CATEGORY, SAVINGS_CATEGORY
from financeguru.repositories import categories as category_repo


def test_init_db_seeds_canonical_categories_in_order():
    assert category_repo.names() == CATEGORIES


def test_savings_and_other_are_protected():
    by_name = {c.name: c for c in category_repo.get_all()}
    assert by_name[SAVINGS_CATEGORY].is_protected
    assert by_name[DEFAULT_CATEGORY].is_protected
    assert not by_name["Food"].is_protected


def test_seeding_is_idempotent():
    import financeguru.db as db

    db.init_db()  # run again on the already-seeded temp DB
    assert category_repo.names() == CATEGORIES


def test_add_appends_after_seeded_categories():
    category_repo.add("Childcare")
    assert category_repo.names()[-1] == "Childcare"


def test_add_duplicate_name_raises_integrity_error():
    with pytest.raises(sqlite3.IntegrityError):
        category_repo.add("Food")


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
