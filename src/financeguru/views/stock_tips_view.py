from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.stock_tip import StockTip
from financeguru.prices import TipFetcher
from financeguru.repositories import stock_tips as tips_repo
from financeguru.views.stock_tip_dialog import StockTipDialog

_PLACEHOLDER = "—"
_GREEN = QColor("#2d9e2d")
_RED = QColor("#c0392b")

_BULLISH = {"Strong Buy", "Buy"}
_BEARISH = {"Strong Sell", "Sell"}

_COLS = [
    "Ticker", "My Action", "My Target", "Confidence",
    "Analyst Consensus", "Analyst Target", "# Analysts", "Notes",
]


class StockTipsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._tips: list[StockTip] = []
        self._fetcher: TipFetcher | None = None

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Tip")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_refresh = QPushButton("Refresh Analyst Data")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        btn_bar.addWidget(self._btn_refresh)
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self._status)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_refresh.clicked.connect(self._on_refresh)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        self._load()

    def _load(self) -> None:
        self._tips = tips_repo.get_all()
        self._render()

    def _render(self) -> None:
        self._table.setRowCount(len(self._tips))
        for row, tip in enumerate(self._tips):
            self._render_row(row, tip)
        count = len(self._tips)
        self._status.setText(f"{count} tip{'s' if count != 1 else ''}")

    def _render_row(self, row: int, tip: StockTip) -> None:
        def _center(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            return item

        def _right(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return item

        def _colored(item: QTableWidgetItem, value: str) -> QTableWidgetItem:
            if value in _BULLISH:
                item.setForeground(_GREEN)
            elif value in _BEARISH:
                item.setForeground(_RED)
            return item

        stars = "★" * tip.confidence + "☆" * (5 - tip.confidence)

        target_str = f"${tip.target_price:,.2f}" if tip.target_price else _PLACEHOLDER
        analyst_target_str = f"${tip.analyst_target:,.2f}" if tip.analyst_target else _PLACEHOLDER
        analyst_count_str = str(tip.analyst_count) if tip.analyst_count else _PLACEHOLDER

        action_item = _colored(_center(tip.action), tip.action)
        analyst_item = _colored(_center(tip.analyst_action or _PLACEHOLDER), tip.analyst_action or "")

        self._table.setItem(row, 0, _center(tip.ticker))
        self._table.setItem(row, 1, action_item)
        self._table.setItem(row, 2, _right(target_str))
        self._table.setItem(row, 3, _center(stars))
        self._table.setItem(row, 4, analyst_item)
        self._table.setItem(row, 5, _right(analyst_target_str))
        self._table.setItem(row, 6, _center(analyst_count_str))
        self._table.setItem(row, 7, QTableWidgetItem(tip.notes or ""))

    def _selected_tip(self) -> StockTip | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        return self._tips[row]

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _on_add(self) -> None:
        dialog = StockTipDialog(self)
        if dialog.exec():
            tips_repo.add(dialog.tip())
            self._load()

    def _on_edit(self) -> None:
        tip = self._selected_tip()
        if tip is None:
            return
        dialog = StockTipDialog(self, tip)
        if dialog.exec():
            tips_repo.update(dialog.tip())
            self._load()

    def _on_delete(self) -> None:
        tip = self._selected_tip()
        if tip is None:
            return
        answer = QMessageBox.question(
            self, "Delete Tip",
            f"Delete tip for {tip.ticker}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            tips_repo.delete(tip.id)
            self._load()

    def _on_refresh(self) -> None:
        if not self._tips:
            return
        tickers = list({t.ticker for t in self._tips})
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.setText("Fetching…")
        self._fetcher = TipFetcher(tickers, self)
        self._fetcher.tips_ready.connect(self._on_tips_ready)
        self._fetcher.fetch_error.connect(self._on_fetch_error)
        self._fetcher.start()

    def _on_tips_ready(self, data: dict) -> None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        for tip in self._tips:
            info = data.get(tip.ticker, {})
            tips_repo.update_analyst_data(
                tip.id,
                info.get("action"),
                info.get("target"),
                info.get("count"),
                now,
            )
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Analyst Data")
        self._load()

    def _on_fetch_error(self, message: str) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Analyst Data")
        QMessageBox.warning(self, "Fetch Failed", f"Could not fetch analyst data:\n{message}")
