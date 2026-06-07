from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QGridLayout, QGroupBox, QLineEdit, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout,
)

from financeguru.budget import INCOME_FREQUENCIES, SPECIFIC_DAYS, parse_pay_days
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
        form.addRow("Amount per Paycheck", self._amount)

        self._frequency = QComboBox()
        self._frequency.addItems(INCOME_FREQUENCIES)
        self._frequency.setCurrentText(income.frequency if income else "biweekly")
        form.addRow("Frequency", self._frequency)

        # ── Pay-days picker (only for "specific days") ────────────────────
        self._days_box = QGroupBox("Pay Days  (day of month)")
        grid = QGridLayout(self._days_box)
        grid.setSpacing(3)
        self._day_buttons: list[QPushButton] = []
        selected = set(parse_pay_days(income.pay_days)) if income else set()
        for day in range(1, 32):
            btn = QPushButton(str(day))
            btn.setCheckable(True)
            btn.setFixedWidth(38)
            btn.setChecked(day in selected)
            self._day_buttons.append(btn)
            grid.addWidget(btn, (day - 1) // 7, (day - 1) % 7)
        form.addRow(self._days_box)

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

        self._frequency.currentTextChanged.connect(self._on_freq_changed)
        self._on_freq_changed(self._frequency.currentText())

    def _on_freq_changed(self, freq: str) -> None:
        self._days_box.setVisible(freq == SPECIFIC_DAYS)
        self.adjustSize()

    def _selected_days(self) -> list[int]:
        return [i for i, btn in enumerate(self._day_buttons, start=1) if btn.isChecked()]

    def accept(self) -> None:
        if self._frequency.currentText() == SPECIFIC_DAYS and not self._selected_days():
            QMessageBox.information(
                self, "Select Pay Days",
                "Pick at least one day of the month, or choose a different frequency.",
            )
            return
        super().accept()

    def income(self) -> Income:
        freq = self._frequency.currentText()
        pay_days = None
        if freq == SPECIFIC_DAYS:
            pay_days = ",".join(str(d) for d in self._selected_days()) or None
        return Income(
            id=self._income_id,
            name=self._name.text().strip(),
            amount=cents(self._amount.value()),
            frequency=freq,
            pay_days=pay_days,
            notes=self._notes.toPlainText().strip() or None,
        )
