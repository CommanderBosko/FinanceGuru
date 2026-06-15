"""Shared pytest fixtures.

Repositories talk to a single SQLite file whose path is the module global
``financeguru.db.DB_PATH``. A pure ``:memory:`` database can't be used because
every repository call opens a fresh connection and an in-memory DB is private to
one connection. Instead each test gets its own temp-file database, created with
the real ``init_db()`` schema so foreign-key cascades and the Decimal<->REAL
round-trip behave exactly as in production.
"""

import pytest

import financeguru.db as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "financeguru"
    monkeypatch.setattr(db, "DB_DIR", db_dir)
    monkeypatch.setattr(db, "DB_PATH", db_dir / "finance.db")
    db.init_db()
    yield db.DB_PATH
