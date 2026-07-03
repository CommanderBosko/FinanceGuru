"""Shared pytest fixtures.

Repositories talk to a single SQLite file whose path is the module global
``financeguru.db.DB_PATH``. A pure ``:memory:`` database can't be used because
every repository call opens a fresh connection and an in-memory DB is private to
one connection. Instead each test gets its own temp-file database, created with
the real ``init_db()`` schema so foreign-key cascades and the Decimal<->REAL
round-trip behave exactly as in production.
"""

import os

import pytest

import financeguru.db as db


@pytest.fixture(scope="session")
def qapp():
    """Process-wide Qt application, shared by every test that needs one.

    Qt allows a single application object per process, and a plain
    QCoreApplication would block widget tests from ever creating the full
    QApplication — so the one shared instance is a QApplication running on the
    offscreen platform (headless; overrides the devShell's "wayland;xcb").
    QThread signal tests only need its event loop and work with it unchanged.
    """
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    db_dir = tmp_path / "financeguru"
    monkeypatch.setattr(db, "DB_DIR", db_dir)
    monkeypatch.setattr(db, "DB_PATH", db_dir / "finance.db")
    db.init_db()
    yield db.DB_PATH
