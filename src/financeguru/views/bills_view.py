from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.bill import Bill
from financeguru.models.payment import Payment
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import payments as payment_repo
from financeguru.views.bill_dialog import BillDialog
from financeguru.views.context_menu import attach_row_menu


class BillsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bills: list[Bill] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Bill")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_pay = QPushButton("Mark Paid")
        for btn in (self._btn_edit, self._btn_delete, self._btn_pay):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addWidget(self._btn_pay)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Name", "Amount", "Due Day", "Recurrence", "Active"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_pay.clicked.connect(self._on_pay)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Bill", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Mark Paid", self._on_pay, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def _refresh(self) -> None:
        self._bills = bill_repo.get_all()
        self._table.setRowCount(len(self._bills))
        for row, bill in enumerate(self._bills):
            amount_item = QTableWidgetItem(f"${bill.amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            due_item = QTableWidgetItem(str(bill.due_day))
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, QTableWidgetItem(bill.name))
            self._table.setItem(row, 1, amount_item)
            self._table.setItem(row, 2, due_item)
            self._table.setItem(row, 3, QTableWidgetItem(bill.recurrence.capitalize()))
            self._table.setItem(row, 4, QTableWidgetItem("Yes" if bill.is_active else "No"))

    def _selected_bill(self) -> Bill | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        return self._bills[row]

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete, self._btn_pay):
            btn.setEnabled(enabled)

    def _on_add(self) -> None:
        dialog = BillDialog(self)
        if dialog.exec():
            bill_repo.add(dialog.bill())
            self._refresh()

    def _on_edit(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        dialog = BillDialog(self, bill)
        if dialog.exec():
            bill_repo.update(dialog.bill())
            self._refresh()

    def _on_delete(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete Bill",
            f"Delete '{bill.name}'? All associated payments will also be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            bill_repo.delete(bill.id)
            self._refresh()

    def _on_pay(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        payment_repo.add(Payment(
            bill_id=bill.id,
            amount=bill.amount,
            paid_date=date.today().isoformat(),
        ))
        QMessageBox.information(
            self, "Payment Recorded",
            f"'{bill.name}' marked as paid on {date.today().strftime('%B %d, %Y')}."
        )
