"""Round-trip tests for the generic key/value preferences store.

First consumer is the Currency Converter tab, but the table itself is generic
(see repositories/preferences.py), so these tests stay currency-agnostic.
"""

from financeguru.repositories import preferences as prefs_repo


def test_get_returns_none_when_missing(temp_db):
    assert prefs_repo.get("nope") is None


def test_get_returns_given_default_when_missing(temp_db):
    assert prefs_repo.get("nope", "fallback") == "fallback"


def test_set_then_get_round_trips(temp_db):
    prefs_repo.set("currency_converter.from", "GBP")
    assert prefs_repo.get("currency_converter.from") == "GBP"


def test_set_upserts_rather_than_duplicating(temp_db):
    prefs_repo.set("k", "v1")
    prefs_repo.set("k", "v2")
    assert prefs_repo.get("k") == "v2"


def test_set_many_writes_all_keys(temp_db):
    prefs_repo.set_many({"a": "1", "b": "2", "c": "3"})
    assert prefs_repo.get("a") == "1"
    assert prefs_repo.get("b") == "2"
    assert prefs_repo.get("c") == "3"


def test_set_many_upserts_existing_keys(temp_db):
    prefs_repo.set("a", "old")
    prefs_repo.set_many({"a": "new", "b": "2"})
    assert prefs_repo.get("a") == "new"
    assert prefs_repo.get("b") == "2"
