from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.expense import Expense
from financeguru.repositories import expenses as expense_repo
from financeguru.views.category_dialog import CategoryDialog
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.expense_dialog import ExpenseDialog
from financeguru.views._month_filter import MonthKey, month_entries, month_prefix
from financeguru.views._table import money, right


class ExpensesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expenses: list[Expense] = []
        # The currently filtered (year, month), or None for "All". Owned
        # locally so this view still works standalone (tests, qt-smoke); under
        # MainWindow it's driven by the global month selector via
        # select_month()/select_all() below.
        self._current_key: MonthKey = (date.today().year, date.today().month)

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Expense")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        self._btn_categories = QPushButton("Manage Categories…")
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search amounts, dates, categories, notes…")
        self._search.setClearButtonEnabled(True)
        btn_bar.addWidget(self._search)
        btn_bar.addWidget(self._btn_categories)
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Amount", "Date", "Category", "Notes"])
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_categories.clicked.connect(self._on_manage_categories)
        self._search.textChanged.connect(self._refresh)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Expense", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def refresh(self) -> None:
        self._refresh()

    def month_keys(self) -> list[tuple[int, int]]:
        """(year, month) keys this tab currently considers interesting —
        every month from the earliest expense on record through today.

        Used by MainWindow to build the global month selector's entries.
        """
        expenses = expense_repo.get_all()  # sorted DESC, so the last row is earliest
        earliest = expenses[-1].spent_date if expenses else None
        return [key for _, key in month_entries(earliest, include_all=False)]

    def select_month(self, year: int, month: int) -> None:
        """Programmatically select `(year, month)` as the current filter."""
        self._current_key = (year, month)
        self._refresh()

    def select_all(self) -> None:
        """Programmatically select "All" as the current filter."""
        self._current_key = None
        self._refresh()

    def _refresh(self) -> None:
        expenses = expense_repo.get_all()  # sorted DESC, so the last row is earliest
        key = self._current_key
        if key is not None:
            prefix = month_prefix(key)
            expenses = [e for e in expenses if (e.spent_date or "").startswith(prefix)]
        query = self._search.text().strip().lower()
        if query:
            expenses = [e for e in expenses if query in self._haystack(e)]
        self._expenses = expenses
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._expenses))
        for row, expense in enumerate(self._expenses):
            amount_item = right(money(expense.amount), float(expense.amount))
            amount_item.setData(Qt.ItemDataRole.UserRole, expense)
            self._table.setItem(row, 0, amount_item)
            self._table.setItem(row, 1, QTableWidgetItem(expense.spent_date))
            self._table.setItem(row, 2, QTableWidgetItem(expense.category))
            self._table.setItem(row, 3, QTableWidgetItem(expense.notes or ""))
        self._table.setSortingEnabled(True)

    @staticmethod
    def _haystack(expense: Expense) -> str:
        """Lowercased, searchable text spanning an expense's display fields."""
        return " ".join((
            money(expense.amount),
            expense.spent_date or "",
            expense.category or "",
            expense.notes or "",
        )).lower()

    def _selected_expense(self) -> Expense | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _on_manage_categories(self) -> None:
        # Pickers read categories from the DB each time they open, so no refresh
        # of this view is needed after the user edits the category list.
        CategoryDialog(self).exec()

    def _on_add(self) -> None:
        dialog = ExpenseDialog(self)
        if dialog.exec():
            expense_repo.add(dialog.expense())
            self._refresh()

    def _on_edit(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        dialog = ExpenseDialog(self, expense)
        if dialog.exec():
            expense_repo.update(dialog.expense())
            self._refresh()

    def _on_delete(self) -> None:
        expense = self._selected_expense()
        if expense is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete Expense",
            f"Delete this {money(expense.amount)} expense?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            expense_repo.delete(expense.id)
            self._refresh()
