from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QLineEdit, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.repositories import payments as payment_repo
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.payment_dialog import PaymentDialog
from financeguru.views._month_filter import month_entries, month_prefix
from financeguru.views._table import money


class PaymentsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[dict] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Payment")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        self._month_picker = QComboBox()
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addWidget(self._month_picker)
        btn_bar.addStretch()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search bills, amounts, dates, notes…")
        self._search.setClearButtonEnabled(True)
        btn_bar.addWidget(self._search)
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
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._month_picker.currentIndexChanged.connect(self._refresh)
        self._search.textChanged.connect(self._refresh)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Payment", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def refresh(self) -> None:
        # Public hook MainWindow calls after a DB restore / on tab switch (e.g.
        # when a bill is renamed in another tab).
        self._refresh()

    def _refresh(self) -> None:
        rows = payment_repo.get_all()  # sorted DESC, so the last row is earliest
        earliest = rows[-1]["paid_date"] if rows else None
        self._populate_month_picker(earliest)
        key = self._month_picker.currentData()
        if key is not None:
            prefix = month_prefix(key)
            rows = [r for r in rows if (r["paid_date"] or "").startswith(prefix)]
        query = self._search.text().strip().lower()
        if query:
            rows = [r for r in rows if query in self._haystack(r)]
        self._rows = rows
        self._table.setRowCount(len(self._rows))
        for row, rec in enumerate(self._rows):
            amount_item = QTableWidgetItem(money(rec['amount']))
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            date_item = QTableWidgetItem(rec["paid_date"])
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, QTableWidgetItem(rec["bill_name"] or "Manual"))
            self._table.setItem(row, 1, amount_item)
            self._table.setItem(row, 2, date_item)
            self._table.setItem(row, 3, QTableWidgetItem(rec["notes"] or ""))

    def _populate_month_picker(self, earliest_date: str | None) -> None:
        """Rebuild the month dropdown, preserving the selection by label if possible.

        Called from `_refresh` (which already has the freshest data on hand for
        `earliest_date`), so the list grows as new history is added instead of
        needing a separate refresh path.
        """
        previous = self._month_picker.currentText()
        entries = month_entries(earliest_date)
        labels = [label for label, _ in entries]

        self._month_picker.blockSignals(True)
        self._month_picker.clear()
        for label, key in entries:
            self._month_picker.addItem(label, key)
        if previous in labels:
            self._month_picker.setCurrentIndex(labels.index(previous))
        else:
            # First population, or the prior selection vanished — default to
            # the current month, which is always index 1 (index 0 is "All").
            self._month_picker.setCurrentIndex(1 if len(labels) > 1 else 0)
        self._month_picker.blockSignals(False)

    @staticmethod
    def _haystack(rec: dict) -> str:
        """Lowercased, searchable text spanning a payment's display fields."""
        return " ".join((
            rec["bill_name"] or "Manual",
            money(rec['amount']),
            rec["paid_date"] or "",
            rec["notes"] or "",
        )).lower()

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _on_add(self) -> None:
        dialog = PaymentDialog(self)
        if dialog.exec():
            payment_repo.add(dialog.payment())
            self._refresh()

    def _on_edit(self) -> None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return
        dialog = PaymentDialog(self, self._rows[row])
        if dialog.exec():
            payment_repo.update(dialog.payment())
            self._refresh()

    def _on_delete(self) -> None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return
        rec = self._rows[row]
        answer = QMessageBox.question(
            self,
            "Delete Payment",
            f"Delete this payment of {money(rec['amount'])} on {rec['paid_date']}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            payment_repo.delete(rec["id"])
            self._refresh()
