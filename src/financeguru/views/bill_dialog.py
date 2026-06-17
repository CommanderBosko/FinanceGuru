import calendar
from datetime import date

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QVBoxLayout,
)
from financeguru.categories import CATEGORIES
from financeguru.models.bill import Bill
from financeguru.money import cents


class BillDialog(QDialog):
    def __init__(self, parent=None, bill: Bill | None = None):
        super().__init__(parent)
        self._bill_id = bill.id if bill else None
        self.setWindowTitle("Edit Bill" if bill else "Add Bill")
        self.setMinimumWidth(360)

        self._form = form = QFormLayout()

        self._name = QLineEdit(bill.name if bill else "")
        form.addRow("Name", self._name)

        self._amount = QDoubleSpinBox()
        self._amount.setPrefix("$")
        self._amount.setRange(0.0, 99_999.99)
        self._amount.setDecimals(2)
        self._amount.setValue(float(bill.amount) if bill else 0.0)
        form.addRow("Amount", self._amount)

        self._due_day = QSpinBox()
        self._due_day.setRange(1, 31)
        self._due_day.setValue(bill.due_day if bill else 1)
        form.addRow("Due Day of Month", self._due_day)

        self._recurrence = QComboBox()
        self._recurrence.addItems(["monthly", "yearly", "one-time"])
        if bill:
            self._recurrence.setCurrentText(bill.recurrence)
        form.addRow("Recurrence", self._recurrence)

        # Only yearly bills fall due in a specific month; the picker is hidden
        # for monthly/one-time recurrence (see _on_recurrence_changed).
        self._due_month = QComboBox()
        for m in range(1, 13):
            self._due_month.addItem(calendar.month_name[m], m)
        if bill and bill.due_month:
            self._due_month.setCurrentIndex(bill.due_month - 1)
        else:
            self._due_month.setCurrentIndex(date.today().month - 1)
        form.addRow("Due Month", self._due_month)
        self._recurrence.currentTextChanged.connect(self._on_recurrence_changed)

        self._category = QComboBox()
        self._category.addItems(CATEGORIES)
        if bill:
            self._category.setCurrentText(bill.category)
        form.addRow("Category", self._category)

        self._notes = QTextEdit(bill.notes or "" if bill else "")
        self._notes.setFixedHeight(64)
        form.addRow("Notes", self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        self._on_recurrence_changed(self._recurrence.currentText())

    def _on_recurrence_changed(self, recurrence: str) -> None:
        self._form.setRowVisible(self._due_month, recurrence == "yearly")

    def bill(self) -> Bill:
        recurrence = self._recurrence.currentText()
        return Bill(
            id=self._bill_id,
            name=self._name.text().strip(),
            amount=cents(self._amount.value()),
            due_day=self._due_day.value(),
            due_month=self._due_month.currentData() if recurrence == "yearly" else None,
            recurrence=recurrence,
            category=self._category.currentText(),
            notes=self._notes.toPlainText().strip() or None,
        )
