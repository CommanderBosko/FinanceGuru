from collections.abc import Callable

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QMenu, QTableWidget

# An action spec is (label, callback, needs_selection). A None entry in the
# action list renders as a separator.
ActionSpec = tuple[str, Callable[[], None], bool]


def attach_row_menu(table: QTableWidget, actions: list[ActionSpec | None]) -> None:
    """Give a table a right-click context menu mirroring its toolbar buttons.

    Right-clicking selects the row under the cursor first, so menu actions
    operate on the clicked row. Actions with ``needs_selection=True`` are
    disabled when no row is selected.
    """

    def show_menu(pos: QPoint) -> None:
        index = table.indexAt(pos)
        if index.isValid():
            table.selectRow(index.row())
        has_selection = bool(table.selectedItems())

        menu = QMenu(table)
        for spec in actions:
            if spec is None:
                menu.addSeparator()
                continue
            label, callback, needs_selection = spec
            action = menu.addAction(label)
            action.setEnabled(has_selection or not needs_selection)
            action.triggered.connect(callback)
        if not menu.isEmpty():
            menu.exec(table.viewport().mapToGlobal(pos))

    table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    table.customContextMenuRequested.connect(show_menu)
