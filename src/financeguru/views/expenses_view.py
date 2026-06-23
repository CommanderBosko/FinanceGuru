from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.expense import Expense
from financeguru.repositories import expenses as expense_repo
from financeguru.views.category_dialog import CategoryDialog
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.expense_dialog import ExpenseDialog


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
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
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
        self._expenses = expense_repo.get_all()
        self._table.setRowCount(len(self._expenses))
        for row, expense in enumerate(self._expenses):
            amount_item = QTableWidgetItem(f"${expense.amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 0, amount_item)
            self._table.setItem(row, 1, QTableWidgetItem(expense.spent_date))
            self._table.setItem(row, 2, QTableWidgetItem(expense.category))
            self._table.setItem(row, 3, QTableWidgetItem(expense.notes or ""))

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
            f"Delete this ${expense.amount:.2f} expense?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            expense_repo.delete(expense.id)
            self._refresh()
