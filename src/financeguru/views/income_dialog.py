from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QTextEdit, QVBoxLayout,
)

from financeguru.models.income import Income
from financeguru.money import cents


class IncomeDialog(QDialog):
    def __init__(self, parent=None, income: Income | None = None):
        super().__init__(parent)
        self._income_id = income.id if income else None
        self.setWindowTitle("Edit Paycheck" if income else "Add Paycheck")
        self.setMinimumWidth(360)

        form = QFormLayout()

        self._name = QLineEdit(income.name if income else "")
        self._name.setPlaceholderText("e.g. Bosko — Main Job")
        form.addRow("Source", self._name)

        self._amount = QDoubleSpinBox()
        self._amount.setPrefix("$")
        self._amount.setRange(0.0, 9_999_999.99)
        self._amount.setDecimals(2)
        self._amount.setValue(float(income.amount) if income else 0.0)
        form.addRow("Amount", self._amount)

        self._pay_date = QDateEdit(
            QDate.fromString(income.pay_date, "yyyy-MM-dd") if income else QDate.currentDate()
        )
        self._pay_date.setCalendarPopup(True)
        self._pay_date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date", self._pay_date)

        self._notes = QTextEdit(income.notes or "" if income else "")
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

    def income(self) -> Income:
        return Income(
            id=self._income_id,
            name=self._name.text().strip(),
            amount=cents(self._amount.value()),
            pay_date=self._pay_date.date().toString("yyyy-MM-dd"),
            notes=self._notes.toPlainText().strip() or None,
        )
