from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.expense import Expense
from financeguru.repositories import expenses as expense_repo
from financeguru.views.category_dialog import CategoryDialog
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.expense_dialog import ExpenseDialog
from financeguru.views._month_filter import month_entries, month_prefix
from financeguru.views._table import money


class ExpensesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._expenses: list[Expense] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Expense")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        self._btn_categories = QPushButton("Manage Categories…")
        # Same filter pair as the Payments tab: expenses accumulate forever,
        # so default to the current month and let search cut across history.
        self._month_picker = QComboBox()
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addWidget(self._month_picker)
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
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_categories.clicked.connect(self._on_manage_categories)
        self._month_picker.currentIndexChanged.connect(self._refresh)
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

    def _refresh(self) -> None:
        expenses = expense_repo.get_all()  # sorted DESC, so the last row is earliest
        earliest = expenses[-1].spent_date if expenses else None
        self._populate_month_picker(earliest)
        key = self._month_picker.currentData()
        if key is not None:
            prefix = month_prefix(key)
            expenses = [e for e in expenses if (e.spent_date or "").startswith(prefix)]
        query = self._search.text().strip().lower()
        if query:
            expenses = [e for e in expenses if query in self._haystack(e)]
        self._expenses = expenses
        self._table.setRowCount(len(self._expenses))
        for row, expense in enumerate(self._expenses):
            amount_item = QTableWidgetItem(money(expense.amount))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 0, amount_item)
            self._table.setItem(row, 1, QTableWidgetItem(expense.spent_date))
            self._table.setItem(row, 2, QTableWidgetItem(expense.category))
            self._table.setItem(row, 3, QTableWidgetItem(expense.notes or ""))

    def _populate_month_picker(self, earliest_date: str | None) -> None:
        """Rebuild the month dropdown, preserving the selection by label if possible.

        Called from `_refresh` (which already has the freshest data on hand for
        `earliest_date`), so the list grows as new history is added instead of
        needing a separate refresh path.
        """
        previous = self._month_picker.currentText()
        entries = month_entries(earliest_date)
        labels = [label for label, _ in entries]

        self._month_picker.blockSignals(True)
        self._month_picker.clear()
        for label, key in entries:
            self._month_picker.addItem(label, key)
        if previous in labels:
            self._month_picker.setCurrentIndex(labels.index(previous))
        else:
            # First population, or the prior selection vanished — default to
            # the current month, which is always index 1 (index 0 is "All").
            self._month_picker.setCurrentIndex(1 if len(labels) > 1 else 0)
        self._month_picker.blockSignals(False)

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
        return self._expenses[row]

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
