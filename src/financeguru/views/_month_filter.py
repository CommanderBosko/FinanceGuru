"""Shared month/year picker logic for views that filter by calendar month.

The Expenses and Payments tabs both need the same "All" + every calendar
month back to the earliest record dropdown, defaulting to the current month.
Kept in one place so the two views can't drift on the entry list or label
format.
"""

from __future__ import annotations

from datetime import date

MonthKey = tuple[int, int] | None


def month_entries(earliest_date: str | None) -> list[tuple[str, MonthKey]]:
    """(label, (year, month)) pairs for a month/year picker, newest first.

    The first entry is always ``("All", None)``. Then every calendar month
    from the current month back through the month of `earliest_date` (a
    "YYYY-MM..." string, or None if there's no data yet), including months
    with no activity, so the list has no gaps.
    """
    entries: list[tuple[str, MonthKey]] = [("All", None)]
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
