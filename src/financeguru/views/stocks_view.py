from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.stock import Stock
from financeguru.money import ZERO, to_decimal
from financeguru.prices import PriceFetcher, stop_fetcher
from financeguru.repositories import stocks as stock_repo
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.stock_dialog import StockDialog

_PLACEHOLDER = "—"
_GREEN = QColor("#2d9e2d")
_RED = QColor("#c0392b")


class StocksView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._stocks: list[Stock] = []
        self._prices: dict[str, float | None] = {}
        self._fetcher: PriceFetcher | None = None

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Position")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_refresh = QPushButton("Refresh Prices")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        btn_bar.addWidget(self._btn_refresh)
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 9)
        self._table.setHorizontalHeaderLabels([
            "Ticker", "Shares", "Avg Cost", "Cost Basis",
            "Current Price", "Market Value", "Gain/Loss $", "Gain/Loss %", "Notes",
        ])
        self._table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._footer = QLabel()
        self._footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._footer)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_refresh.clicked.connect(self._on_refresh)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Position", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
            None,
            ("Refresh Prices", self._on_refresh, False),
        ])

        self._refresh()

    def _refresh(self) -> None:
        self._stocks = stock_repo.get_all()
        self._table.setRowCount(len(self._stocks))
        total_cost = ZERO
        total_market = ZERO
        has_prices = bool(self._prices)

        for row, stock in enumerate(self._stocks):
            cost_basis = stock.shares * stock.purchase_price
            total_cost += cost_basis
            raw_price = self._prices.get(stock.ticker)
            current = to_decimal(raw_price) if raw_price is not None else None

            def _right(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                return item

            def _center(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            shares_str = f"{stock.shares:,.4f}".rstrip("0").rstrip(".")
            self._table.setItem(row, 0, _center(stock.ticker))
            self._table.setItem(row, 1, _right(shares_str))
            self._table.setItem(row, 2, _right(f"${stock.purchase_price:,.2f}"))
            self._table.setItem(row, 3, _right(f"${cost_basis:,.2f}"))

            if current is not None:
                market_value = stock.shares * current
                gain = market_value - cost_basis
                gain_pct = (gain / cost_basis * 100) if cost_basis else 0.0
                total_market += market_value
                color = _GREEN if gain >= 0 else _RED

                price_item = _right(f"${current:,.2f}")
                mv_item = _right(f"${market_value:,.2f}")
                gain_item = _right(f"${gain:+,.2f}")
                pct_item = _right(f"{gain_pct:+.2f}%")
                for item in (gain_item, pct_item):
                    item.setForeground(color)

                self._table.setItem(row, 4, price_item)
                self._table.setItem(row, 5, mv_item)
                self._table.setItem(row, 6, gain_item)
                self._table.setItem(row, 7, pct_item)
            else:
                for col in range(4, 8):
                    self._table.setItem(row, col, _center(_PLACEHOLDER))

            self._table.setItem(row, 8, QTableWidgetItem(stock.notes or ""))

        parts = [f"Cost basis: ${total_cost:,.2f}"]
        if has_prices and total_market:
            total_gain = total_market - total_cost
            pct = (total_gain / total_cost * 100) if total_cost else 0.0
            parts.append(f"Market value: ${total_market:,.2f}")
            parts.append(f"Total gain/loss: ${total_gain:+,.2f} ({pct:+.2f}%)")
        self._footer.setText("   |   ".join(parts))

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
            self, "Delete Position",
            f"Delete {stock.ticker} position ({stock.shares} shares)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            stock_repo.delete(stock.id)
            self._refresh()

    def _on_refresh(self) -> None:
        if not self._stocks:
            return
        tickers = list({s.ticker for s in self._stocks})
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.setText("Fetching…")
        # The previous fetcher (guaranteed finished — the button is re-enabled
        # only on finish) stays parented to this view; free it so repeated
        # refreshes don't pile up dead QThread children.
        if self._fetcher is not None:
            self._fetcher.deleteLater()
        fetcher = PriceFetcher(tickers, self)
        self._fetcher = fetcher
        fetcher.prices_ready.connect(self._on_prices_ready)
        fetcher.fetch_error.connect(self._on_fetch_error)
        fetcher.partial_error.connect(self._on_partial_error)
        fetcher.finished.connect(self._restore_refresh_button)
        fetcher.start()

    def _restore_refresh_button(self) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Prices")

    def stop_threads(self) -> None:
        # Called by MainWindow.closeEvent on quit. This view is nested in a
        # QTabWidget and never receives its own close event, so cleanup can't
        # live in closeEvent — the parent window drives it.
        stop_fetcher(self._fetcher)

    def _on_prices_ready(self, prices: dict) -> None:
        self._prices = prices
        self._refresh()
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Prices")

    def _on_fetch_error(self, message: str) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Prices")
        QMessageBox.warning(self, "Price Fetch Failed", f"Could not fetch prices:\n{message}")

    def _on_partial_error(self, tickers: list) -> None:
        QMessageBox.warning(
            self,
            "Some Prices Unavailable",
            "Could not fetch a price for: "
            + ", ".join(tickers)
            + ".\n\nThis is usually a temporary network or rate-limit issue. "
            "Try refreshing again shortly.",
        )
