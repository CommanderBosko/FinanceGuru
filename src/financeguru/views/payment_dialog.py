from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QTextEdit, QVBoxLayout,
)

from financeguru.models.bill import Bill
from financeguru.models.payment import Payment
from financeguru.money import cents
from financeguru.repositories import bills as bill_repo

_NO_BILL = "— No bill —"


class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Payment")
        self.setMinimumWidth(360)

        self._bills: list[Bill] = bill_repo.get_all()

        form = QFormLayout()

        self._bill_combo = QComboBox()
        self._bill_combo.addItem(_NO_BILL, userData=None)
        for bill in self._bills:
            self._bill_combo.addItem(bill.name, userData=bill)
        self._bill_combo.currentIndexChanged.connect(self._on_bill_changed)
        form.addRow("Bill", self._bill_combo)

        self._amount = QDoubleSpinBox()
        self._amount.setPrefix("$")
        self._amount.setRange(0.0, 99_999.99)
        self._amount.setDecimals(2)
        form.addRow("Amount", self._amount)

        self._date = QDateEdit(QDate.currentDate())
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Date", self._date)

        self._notes = QTextEdit()
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

    def _on_bill_changed(self, index: int) -> None:
        bill: Bill | None = self._bill_combo.itemData(index)
        if bill is not None:
            self._amount.setValue(float(bill.amount))

    def payment(self) -> Payment:
        bill: Bill | None = self._bill_combo.currentData()
        return Payment(
            bill_id=bill.id if bill else None,
            amount=cents(self._amount.value()),
            paid_date=self._date.date().toString("yyyy-MM-dd"),
            notes=self._notes.toPlainText().strip() or None,
        )
