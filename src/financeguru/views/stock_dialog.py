from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
    QLineEdit, QDateEdit, QTextEdit, QVBoxLayout,
)

from financeguru.models.stock import Stock


class StockDialog(QDialog):
    def __init__(self, parent=None, stock: Stock | None = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Position" if stock else "Add Position")
        self.setMinimumWidth(360)
        self._stock_id = stock.id if stock else None

        form = QFormLayout()

        self._ticker = QLineEdit(stock.ticker if stock else "")
        self._ticker.setPlaceholderText("e.g. AAPL")
        form.addRow("Ticker", self._ticker)

        self._shares = QDoubleSpinBox()
        self._shares.setRange(0.0001, 999_999.0)
        self._shares.setDecimals(4)
        self._shares.setValue(stock.shares if stock else 1.0)
        form.addRow("Shares", self._shares)

        self._price = QDoubleSpinBox()
        self._price.setPrefix("$")
        self._price.setRange(0.01, 999_999.99)
        self._price.setDecimals(2)
        self._price.setValue(stock.purchase_price if stock else 0.0)
        form.addRow("Purchase Price", self._price)

        purchase_date = QDate.fromString(stock.purchase_date, "yyyy-MM-dd") if stock else QDate.currentDate()
        self._date = QDateEdit(purchase_date)
        self._date.setCalendarPopup(True)
        self._date.setDisplayFormat("yyyy-MM-dd")
        form.addRow("Purchase Date", self._date)

        self._notes = QTextEdit(stock.notes or "" if stock else "")
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

    def stock(self) -> Stock:
        return Stock(
            id=self._stock_id,
            ticker=self._ticker.text().strip().upper(),
            shares=self._shares.value(),
            purchase_price=self._price.value(),
            purchase_date=self._date.date().toString("yyyy-MM-dd"),
            notes=self._notes.toPlainText().strip() or None,
        )
