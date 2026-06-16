from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QTextEdit, QVBoxLayout,
)

from financeguru.categories import CATEGORIES, DEFAULT_CATEGORY
from financeguru.models.expense import Expense
from financeguru.money import cents


class ExpenseDialog(QDialog):
    def __init__(self, parent=None, expense: Expense | None = None):
        super().__init__(parent)
        self._expense_id = expense.id if expense else None
        self.setWindowTitle("Edit Expense" if expense else "Add Expense")
        self.setMinimumWidth(360)

        form = QFormLayout()

        self._amount = QDoubleSpinBox()
        self._amount.setPrefix("$")
        self._amount.setRange(0.0, 99_999.99)
        self._amount.setDecimals(2)
        form.addRow("Amount", self._amount)

        self._date = QDateEdit(QDate.currentDate())
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date", self._date)

        self._category = QComboBox()
        self._category.addItems(CATEGORIES)
        self._category.setCurrentText(DEFAULT_CATEGORY)
        form.addRow("Category", self._category)

        self._notes = QTextEdit()
        self._notes.setFixedHeight(64)
        form.addRow("Notes", self._notes)

        if expense:
            self._prefill(expense)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _prefill(self, expense: Expense) -> None:
        self._amount.setValue(float(expense.amount))
        self._date.setDate(QDate.fromString(expense.spent_date, "yyyy-MM-dd"))
        self._category.setCurrentText(expense.category)
        self._notes.setPlainText(expense.notes or "")

    def expense(self) -> Expense:
        return Expense(
            id=self._expense_id,
            amount=cents(self._amount.value()),
            spent_date=self._date.date().toString("yyyy-MM-dd"),
            category=self._category.currentText(),
            notes=self._notes.toPlainText().strip() or None,
        )
