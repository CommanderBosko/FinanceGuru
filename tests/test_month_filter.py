"""Unit tests for the shared month/year picker helper.

`populate_month_picker` used to be copy-pasted nearly verbatim across
PaymentsView, ExpensesView, and SalaryView; it now lives here once and each
view's own tests (test_payments_view.py, test_expenses_view.py,
test_salary_view.py) exercise it indirectly through the widget. These tests
cover the helper directly, in isolation from any view.
"""

from datetime import date

from PySide6.QtWidgets import QComboBox

from financeguru.views._month_filter import populate_from_keys, populate_month_picker


def test_populates_all_plus_every_month_back_to_earliest(qapp):
    combo = QComboBox()
    populate_month_picker(combo, "2025-01-15")

    labels = [combo.itemText(i) for i in range(combo.count())]
    assert labels[0] == "All"
    assert labels[1] == date.today().strftime("%B %Y")
    assert labels[-1] == "January 2025"


def test_defaults_to_current_month_on_first_population(qapp):
    combo = QComboBox()
    populate_month_picker(combo, None)
    assert combo.currentIndex() == 1
    assert combo.currentText() == date.today().strftime("%B %Y")


def test_only_all_and_current_month_when_earliest_is_this_month(qapp):
    combo = QComboBox()
    # An earliest_date in the current month means only "All" and the current
    # month exist — still expect index 1 (current month), not "All".
    populate_month_picker(combo, date.today().isoformat())
    assert combo.count() == 2
    assert combo.currentIndex() == 1


def test_preserves_selection_by_label_across_repopulation(qapp):
    combo = QComboBox()
    populate_month_picker(combo, "2025-01-15")
    labels = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(labels.index("January 2025"))

    # Re-populate (e.g. a fresh refresh) with the same earliest date — the
    # previously selected label should still be selected, not reset.
    populate_month_picker(combo, "2025-01-15")
    assert combo.currentText() == "January 2025"


def test_falls_back_to_current_month_when_previous_selection_vanishes(qapp):
    combo = QComboBox()
    populate_month_picker(combo, "2025-01-15")
    labels = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(labels.index("January 2025"))

    # Re-populate with a later earliest date — "January 2025" no longer
    # exists in the list, so selection must fall back to the current month.
    populate_month_picker(combo, date.today().isoformat())
    assert combo.currentIndex() == 1
    assert combo.currentText() == date.today().strftime("%B %Y")


# --- include_all=False (the Notes tab's picker) -----------------------------

def test_include_all_false_omits_the_all_entry(qapp):
    combo = QComboBox()
    populate_month_picker(combo, "2025-01-15", include_all=False)

    labels = [combo.itemText(i) for i in range(combo.count())]
    assert "All" not in labels
    assert labels[0] == date.today().strftime("%B %Y")
    assert labels[-1] == "January 2025"


def test_include_all_false_defaults_to_current_month_at_index_zero(qapp):
    combo = QComboBox()
    populate_month_picker(combo, None, include_all=False)
    assert combo.currentIndex() == 0
    assert combo.currentText() == date.today().strftime("%B %Y")


def test_include_all_false_preserves_selection_across_repopulation(qapp):
    combo = QComboBox()
    populate_month_picker(combo, "2025-01-15", include_all=False)
    labels = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(labels.index("January 2025"))

    populate_month_picker(combo, "2025-01-15", include_all=False)
    assert combo.currentText() == "January 2025"


# --- populate_from_keys (MainWindow's global month selector) ----------------


def test_populate_from_keys_builds_all_plus_every_key_sorted_newest_first(qapp):
    combo = QComboBox()
    populate_from_keys(combo, {(2025, 1), (2026, 3), (2025, 6)})

    labels = [combo.itemText(i) for i in range(combo.count())]
    assert labels[0] == "All"
    # Sparse, not contiguous — unlike month_entries' earliest-to-today fill,
    # there's no "February 2026" entry just because January and March exist.
    assert labels[1:] == ["March 2026", "June 2025", "January 2025"]


def test_populate_from_keys_defaults_to_current_month_when_present(qapp):
    combo = QComboBox()
    today = date.today()
    populate_from_keys(combo, {(today.year, today.month), (2020, 1)})
    assert combo.currentText() == today.strftime("%B %Y")


def test_populate_from_keys_falls_back_to_all_when_current_month_absent(qapp):
    combo = QComboBox()
    # Neither key is the current month — every contributing tab seeds it in
    # practice, but this helper itself must still degrade gracefully.
    populate_from_keys(combo, {(2020, 1), (2019, 5)})
    assert combo.currentText() == "All"


def test_populate_from_keys_preserves_selection_across_repopulation(qapp):
    combo = QComboBox()
    keys = {(2025, 1), (2026, 3)}
    populate_from_keys(combo, keys)
    labels = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(labels.index("January 2025"))

    populate_from_keys(combo, keys)
    assert combo.currentText() == "January 2025"


def test_populate_from_keys_falls_back_to_current_month_when_previous_selection_vanishes(qapp):
    combo = QComboBox()
    today = date.today()
    populate_from_keys(combo, {(2025, 1), (today.year, today.month)})
    labels = [combo.itemText(i) for i in range(combo.count())]
    combo.setCurrentIndex(labels.index("January 2025"))

    # Re-populate without (2025, 1) — the previous selection vanished, so
    # this falls back to the current month (present) rather than "All".
    populate_from_keys(combo, {(today.year, today.month)})
    assert combo.currentText() == today.strftime("%B %Y")
