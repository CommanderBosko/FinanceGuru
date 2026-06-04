from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.repositories import payments as payment_repo
from financeguru.views.payment_dialog import PaymentDialog


class PaymentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Payment")
        self._btn_delete = QPushButton("Delete")
        self._btn_delete.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Bill", "Amount", "Date", "Notes"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_delete.clicked.connect(self._on_delete)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)

        self._refresh()

    def _refresh(self) -> None:
        self._rows = payment_repo.get_all()
        self._table.setRowCount(len(self._rows))
        for row, rec in enumerate(self._rows):
            amount_item = QTableWidgetItem(f"${rec['amount']:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            date_item = QTableWidgetItem(rec["paid_date"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, QTableWidgetItem(rec["bill_name"] or "Manual"))
            self._table.setItem(row, 1, amount_item)
            self._table.setItem(row, 2, date_item)
            self._table.setItem(row, 3, QTableWidgetItem(rec["notes"] or ""))

    def _on_selection_changed(self) -> None:
        self._btn_delete.setEnabled(bool(self._table.selectedItems()))

    def _on_add(self) -> None:
        dialog = PaymentDialog(self)
        if dialog.exec():
            payment_repo.add(dialog.payment())
            self._refresh()

    def _on_delete(self) -> None:
        row = self._table.currentRow()
        if row < 0:
            return
        rec = self._rows[row]
        answer = QMessageBox.question(
            self,
            "Delete Payment",
            f"Delete this payment of ${rec['amount']:,.2f} on {rec['paid_date']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            payment_repo.delete(rec["id"])
            self._refresh()
