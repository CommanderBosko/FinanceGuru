from datetime import datetime, timezone

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.stock_tip import StockTip
from financeguru.prices import TipFetcher, stop_fetcher
from financeguru.repositories import stock_tips as tips_repo
from financeguru.views._month_filter import MonthKey
from financeguru.views._table import center, money, right
from financeguru.views.context_menu import attach_row_menu
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
        # The currently filtered (year, month), or None for "All" — matches
        # this tab's pre-existing behavior (no filtering at all) as the
        # standalone default. Under MainWindow, driven by the global month
        # selector via select_month()/select_all() below, filtering by each
        # tip's own added_date.
        self._current_key: MonthKey = None

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
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(True)
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

        attach_row_menu(self._table, [
            ("Add Tip", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
            None,
            ("Refresh Analyst Data", self._on_refresh, False),
        ])

        self._load()

    def refresh(self) -> None:
        # Public hook MainWindow calls after a DB restore / on tab switch.
        self._load()

    def select_month(self, year: int, month: int) -> None:
        """Programmatically select `(year, month)` as the current filter."""
        self._current_key = (year, month)
        self._render()

    def select_all(self) -> None:
        """Programmatically select "All" as the current filter."""
        self._current_key = None
        self._render()

    def _load(self) -> None:
        self._tips = tips_repo.get_all()
        self._render()

    def _visible_tips(self) -> list[StockTip]:
        if self._current_key is None:
            return self._tips
        year, month = self._current_key
        prefix = f"{year:04d}-{month:02d}"
        return [t for t in self._tips if (t.added_date or "").startswith(prefix)]

    def _render(self) -> None:
        visible = self._visible_tips()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(visible))
        for row, tip in enumerate(visible):
            self._render_row(row, tip)
        self._table.setSortingEnabled(True)
        count = len(visible)
        self._status.setText(f"{count} tip{'s' if count != 1 else ''}")

    def _render_row(self, row: int, tip: StockTip) -> None:
        def _colored(item: QTableWidgetItem, value: str) -> QTableWidgetItem:
            if value in _BULLISH:
                item.setForeground(_GREEN)
            elif value in _BEARISH:
                item.setForeground(_RED)
            return item

        stars = "★" * tip.confidence + "☆" * (5 - tip.confidence)

        target_str = money(tip.target_price) if tip.target_price else _PLACEHOLDER
        analyst_target_str = money(tip.analyst_target) if tip.analyst_target else _PLACEHOLDER
        analyst_count_str = str(tip.analyst_count) if tip.analyst_count else _PLACEHOLDER

        action_item = _colored(center(tip.action), tip.action)
        analyst_item = _colored(center(tip.analyst_action or _PLACEHOLDER), tip.analyst_action or "")

        ticker_item = center(tip.ticker)
        ticker_item.setData(Qt.ItemDataRole.UserRole, tip)
        self._table.setItem(row, 0, ticker_item)
        self._table.setItem(row, 1, action_item)
        self._table.setItem(row, 2, right(target_str, float(tip.target_price) if tip.target_price else float("-inf")))
        self._table.setItem(row, 3, center(stars, tip.confidence))
        self._table.setItem(row, 4, analyst_item)
        self._table.setItem(row, 5, right(analyst_target_str, float(tip.analyst_target) if tip.analyst_target else float("-inf")))
        self._table.setItem(row, 6, center(analyst_count_str, tip.analyst_count if tip.analyst_count else float("-inf")))
        self._table.setItem(row, 7, QTableWidgetItem(tip.notes or ""))

    def _selected_tip(self) -> StockTip | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

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
        # The toolbar button is disabled while a fetch is in flight, but the
        # row context menu's "Refresh Analyst Data" entry has no such guard
        # and can still invoke this handler — without this check it would
        # tear down self._fetcher (a QThread that isRunning()) via
        # deleteLater() below, which is exactly the "QThread destroyed while
        # still running" crash stop_fetcher() elsewhere in the app is built
        # to avoid.
        if self._fetcher is not None and self._fetcher.isRunning():
            return
        if not self._tips:
            return
        tickers = list({t.ticker for t in self._tips})
        self._btn_refresh.setEnabled(False)
        self._btn_refresh.setText("Fetching…")
        # The previous fetcher (guaranteed finished — the button is re-enabled
        # only on finish) stays parented to this view; free it so repeated
        # refreshes don't pile up dead QThread children.
        if self._fetcher is not None:
            self._fetcher.deleteLater()
        self._fetcher = TipFetcher(tickers, self)
        self._fetcher.tips_ready.connect(self._on_tips_ready)
        self._fetcher.fetch_error.connect(self._on_fetch_error)
        self._fetcher.partial_error.connect(self._on_partial_error)
        self._fetcher.finished.connect(self._restore_refresh_button)
        self._fetcher.start()

    def _restore_refresh_button(self) -> None:
        self._btn_refresh.setEnabled(True)
        self._btn_refresh.setText("Refresh Analyst Data")

    def stop_threads(self) -> None:
        # Called by MainWindow.closeEvent on quit. This view is nested in a
        # QTabWidget and never receives its own close event, so cleanup can't
        # live in closeEvent — the parent window drives it.
        stop_fetcher(self._fetcher)

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

    def _on_partial_error(self, tickers: list) -> None:
        QMessageBox.warning(
            self,
            "Some Data Unavailable",
            "Could not fetch analyst data for: "
            + ", ".join(tickers)
            + ".\n\nThis is usually a temporary network or rate-limit issue. "
            "Try refreshing again shortly.",
        )
