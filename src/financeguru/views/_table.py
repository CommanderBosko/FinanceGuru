"""Shared QTableWidgetItem builders.

Every table view needs right- and centre-aligned cells; these were previously
re-declared (often inside per-row loops, rebuilding the closure each iteration)
across the view modules. Import these instead.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

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
