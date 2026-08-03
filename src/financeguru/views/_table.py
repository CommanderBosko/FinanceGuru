"""Shared QTableWidgetItem builders and display formatters.

Every table view needs right- and centre-aligned cells; these were previously
re-declared (often inside per-row loops, rebuilding the closure each iteration)
across the view modules. Import these instead.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem


def money(value) -> str:
    """The one currency display format: ``$1,234.56``.

    Views were each hand-writing the format string, and one (Expenses) drifted
    to a separator-less variant — route every user-visible amount through here
    so the format can't fork again. Accepts Decimal or float.
    """
    return f"${value:,.2f}"

_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_CENTER = Qt.AlignmentFlag.AlignCenter


class SortableItem(QTableWidgetItem):
    """Sorts by an attached key instead of its display text.

    QTableWidget's native column-sort (setSortingEnabled) compares cells with
    ``<``, which for a plain QTableWidgetItem means comparing display text.
    That's wrong for money ("$9.00" would sort after "$100.00"), zero-padded
    numbers ("10" before "9"), and non-ISO dates. right()/center() build one
    of these instead of a plain item whenever a ``sort_key`` is given.
    """

    def __init__(self, text: str, sort_key):
        super().__init__(text)
        self._sort_key = sort_key

    def __lt__(self, other):
        if isinstance(other, SortableItem):
            return self._sort_key < other._sort_key
        return super().__lt__(other)


def right(text: str, sort_key=None) -> QTableWidgetItem:
    """A right-aligned (vertically centred) cell — for amounts and numbers.

    Pass ``sort_key`` (the underlying number) for columns whose display text
    doesn't sort the same way as its value — e.g. ``right(money(x), x)``.
    """
    item = SortableItem(text, sort_key) if sort_key is not None else QTableWidgetItem(text)
    item.setTextAlignment(_RIGHT)
    return item


def center(text: str, sort_key=None) -> QTableWidgetItem:
    """A centre-aligned cell — for short codes, dates, and counts.

    Pass ``sort_key`` for the same reason as in ``right()``.
    """
    item = SortableItem(text, sort_key) if sort_key is not None else QTableWidgetItem(text)
    item.setTextAlignment(_CENTER)
    return item
