"""Shared month/year picker logic for views that filter by calendar month.

The Expenses and Payments tabs both need the same "All" + every calendar
month back to the earliest record dropdown, defaulting to the current month.
Kept in one place so the two views can't drift on the entry list or label
format.
"""

from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import QComboBox

MonthKey = tuple[int, int] | None


def month_entries(earliest_date: str | None, include_all: bool = True) -> list[tuple[str, MonthKey]]:
    """(label, (year, month)) pairs for a month/year picker, newest first.

    The first entry is ``("All", None)`` unless ``include_all`` is False (the
    Notes tab's picker omits it — every note is always filed under exactly
    one month, so there's no unfiltered view to offer). Then every calendar
    month from the current month back through the month of `earliest_date` (a
    "YYYY-MM..." string, or None if there's no data yet), including months
    with no activity, so the list has no gaps.
    """
    entries: list[tuple[str, MonthKey]] = [("All", None)] if include_all else []
    today = date.today()
    year, month = today.year, today.month
    if earliest_date:
        end_year, end_month = int(earliest_date[:4]), int(earliest_date[5:7])
    else:
        end_year, end_month = year, month
    while (year, month) >= (end_year, end_month):
        entries.append((date(year, month, 1).strftime("%B %Y"), (year, month)))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return entries


def month_prefix(key: tuple[int, int]) -> str:
    """The "YYYY-MM-" prefix a stored date string must start with for `key`."""
    year, month = key
    return f"{year:04d}-{month:02d}-"


def populate_month_picker(combo: QComboBox, earliest_date: str | None, include_all: bool = True) -> None:
    """Rebuild `combo` from `month_entries`, preserving the selection by label.

    Shared by every tab with a month/year filter dropdown (Payments, Expenses,
    Salary, Notes, ...). Called from each view's own refresh (which already
    has the freshest data on hand for `earliest_date`), so the list grows as
    new history is added instead of needing a separate refresh path. Pass
    ``include_all=False`` for a picker with no unfiltered view (Notes).
    """
    previous = combo.currentText()
    entries = month_entries(earliest_date, include_all)
    labels = [label for label, _ in entries]

    combo.blockSignals(True)
    combo.clear()
    for label, key in entries:
        combo.addItem(label, key)
    if previous in labels:
        combo.setCurrentIndex(labels.index(previous))
    else:
        # First population, or the prior selection vanished — default to
        # the current month, which is always present (the range always spans
        # down from "today"), whatever index that lands at with/without "All".
        current_label = date.today().strftime("%B %Y")
        combo.setCurrentIndex(labels.index(current_label) if current_label in labels else 0)
    combo.blockSignals(False)
