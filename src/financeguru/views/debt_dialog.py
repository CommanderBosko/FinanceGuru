from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLineEdit, QMessageBox, QTextEdit, QVBoxLayout,
)

from financeguru.models.debt import Debt
from financeguru.money import cents


class DebtDialog(QDialog):
    def __init__(self, parent=None, debt: Debt | None = None):
        super().__init__(parent)
        self._debt = debt
        self.setWindowTitle("Edit Debt" if debt else "Add Debt")
        self.setMinimumWidth(380)

        form = QFormLayout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Chase Credit Card")
        form.addRow("Name:", self._name)

        self._balance = QDoubleSpinBox()
        self._balance.setRange(0.01, 9_999_999)
        self._balance.setDecimals(2)
        self._balance.setPrefix("$")
        form.addRow("Current Balance:", self._balance)

        self._rate = QDoubleSpinBox()
        self._rate.setRange(0, 100)
        self._rate.setDecimals(2)
        self._rate.setSuffix("%")
        form.addRow("APR:", self._rate)

        self._minimum = QDoubleSpinBox()
        self._minimum.setRange(0, 99_999)
        self._minimum.setDecimals(2)
        self._minimum.setPrefix("$")
        form.addRow("Minimum Payment:", self._minimum)

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)
        form.addRow("Notes:", self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        if debt:
            self._name.setText(debt.name)
            self._balance.setValue(float(debt.balance))
            self._rate.setValue(float(debt.interest_rate))
            self._minimum.setValue(float(debt.minimum_payment))
            self._notes.setPlainText(debt.notes or "")

    def _on_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.information(self, "Name Required", "Give the debt a name.")
            self._name.setFocus()
            return
        self.accept()

    def debt(self) -> Debt:
        return Debt(
            id=self._debt.id if self._debt else 0,
            name=self._name.text().strip(),
            balance=cents(self._balance.value()),
            interest_rate=cents(self._rate.value()),
            minimum_payment=cents(self._minimum.value()),
            notes=self._notes.toPlainText().strip() or None,
        )
