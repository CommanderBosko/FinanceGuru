from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.stock import Stock
from financeguru.repositories import stocks as stock_repo
from financeguru.views.stock_dialog import StockDialog


class StocksView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stocks: list[Stock] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Position")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Ticker", "Shares", "Purchase Price", "Purchase Date", "Total Cost", "Notes"]
        )
        self._table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._total_label = QLabel()
        self._total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._total_label)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        self._refresh()

    def _refresh(self) -> None:
        self._stocks = stock_repo.get_all()
        self._table.setRowCount(len(self._stocks))
        total = 0.0
        for row, stock in enumerate(self._stocks):
            cost = stock.shares * stock.purchase_price
            total += cost

            ticker_item = QTableWidgetItem(stock.ticker)
            ticker_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            shares_item = QTableWidgetItem(f"{stock.shares:,.4f}".rstrip("0").rstrip("."))
            shares_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            price_item = QTableWidgetItem(f"${stock.purchase_price:,.2f}")
            price_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            date_item = QTableWidgetItem(stock.purchase_date)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            cost_item = QTableWidgetItem(f"${cost:,.2f}")
            cost_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            self._table.setItem(row, 0, ticker_item)
            self._table.setItem(row, 1, shares_item)
            self._table.setItem(row, 2, price_item)
            self._table.setItem(row, 3, date_item)
            self._table.setItem(row, 4, cost_item)
            self._table.setItem(row, 5, QTableWidgetItem(stock.notes or ""))

        self._total_label.setText(f"Total cost basis:  ${total:,.2f}")

    def _selected_stock(self) -> Stock | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        return self._stocks[row]

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _on_add(self) -> None:
        dialog = StockDialog(self)
        if dialog.exec():
            stock_repo.add(dialog.stock())
            self._refresh()

    def _on_edit(self) -> None:
        stock = self._selected_stock()
        if stock is None:
            return
        dialog = StockDialog(self, stock)
        if dialog.exec():
            stock_repo.update(dialog.stock())
            self._refresh()

    def _on_delete(self) -> None:
        stock = self._selected_stock()
        if stock is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete Position",
            f"Delete {stock.ticker} position ({stock.shares} shares)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            stock_repo.delete(stock.id)
            self._refresh()
