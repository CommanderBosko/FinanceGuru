from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QTextEdit, QVBoxLayout,
)

from financeguru.budget import INCOME_FREQUENCIES
from financeguru.models.income import Income


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
        self._amount.setValue(income.amount if income else 0.0)
        form.addRow("Amount per Paycheck", self._amount)

        self._frequency = QComboBox()
        self._frequency.addItems(INCOME_FREQUENCIES)
        self._frequency.setCurrentText(income.frequency if income else "biweekly")
        form.addRow("Frequency", self._frequency)

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
            amount=self._amount.value(),
            frequency=self._frequency.currentText(),
            notes=self._notes.toPlainText().strip() or None,
        )
