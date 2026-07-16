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


def right(text: str) -> QTableWidgetItem:
    """A right-aligned (vertically centred) cell — for amounts and numbers."""
    item = QTableWidgetItem(text)
    item.setTextAlignment(_RIGHT)
    return item


def center(text: str) -> QTableWidgetItem:
    """A centre-aligned cell — for short codes, dates, and counts."""
    item = QTableWidgetItem(text)
    item.setTextAlignment(_CENTER)
    return item
