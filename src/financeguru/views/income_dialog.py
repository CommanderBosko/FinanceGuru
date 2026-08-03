from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QSpinBox, QTextEdit, QVBoxLayout,
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
        form.addRow("Amount per Month", self._amount)

        self._pay_day = QSpinBox()
        self._pay_day.setRange(1, 31)
        self._pay_day.setValue(income.pay_day if income else 1)
        form.addRow("Pay Day of Month", self._pay_day)

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
            pay_day=self._pay_day.value(),
            notes=self._notes.toPlainText().strip() or None,
        )
