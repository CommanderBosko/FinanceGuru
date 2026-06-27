from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QTextEdit, QVBoxLayout,
)

from financeguru.models.stock_tip import StockTip
from financeguru.money import cents
from financeguru.prices import TipFetcher, stop_fetcher
from financeguru.validators import normalize_ticker

_ACTIONS = ["Watch", "Buy", "Strong Buy", "Hold", "Sell", "Strong Sell"]


class StockTipDialog(QDialog):
    def __init__(self, parent=None, tip: StockTip | None = None):
        super().__init__(parent)
        self._tip = tip
        self._fetcher: TipFetcher | None = None
        self.setWindowTitle("Edit Tip" if tip else "Add Tip")
        self.setMinimumWidth(400)

        form = QFormLayout()

        self._ticker = QLineEdit()
        self._ticker.setPlaceholderText("e.g. AAPL")
        form.addRow("Ticker:", self._ticker)

        self._action = QComboBox()
        self._action.addItems(_ACTIONS)
        form.addRow("Your Action:", self._action)

        self._target = QDoubleSpinBox()
        self._target.setRange(0, 999_999)
        self._target.setDecimals(2)
        self._target.setPrefix("$")
        self._target.setSpecialValueText("—")
        form.addRow("Your Target Price:", self._target)

        self._confidence = QSpinBox()
        self._confidence.setRange(1, 5)
        self._confidence.setValue(3)
        form.addRow("Confidence (1–5):", self._confidence)

        self._notes = QTextEdit()
        self._notes.setFixedHeight(80)
        form.addRow("Notes:", self._notes)

        self._fetch_btn = QPushButton("Fetch Analyst Data")
        self._fetch_status = QLabel()
        self._fetch_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form.addRow(self._fetch_btn, self._fetch_status)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self._fetch_btn.clicked.connect(self._on_fetch)
        self._ticker.textChanged.connect(lambda _: self._fetch_status.setText(""))

        if tip:
            self._ticker.setText(tip.ticker)
            idx = self._action.findText(tip.action)
            if idx >= 0:
                self._action.setCurrentIndex(idx)
            self._target.setValue(float(tip.target_price) if tip.target_price else 0.0)
            self._confidence.setValue(tip.confidence)
            self._notes.setPlainText(tip.notes or "")
            self._ticker.setReadOnly(True)

    def _on_fetch(self) -> None:
        ticker = normalize_ticker(self._ticker.text())
        if ticker is None:
            self._fetch_status.setText("Enter a valid ticker first.")
            return
        self._fetch_btn.setEnabled(False)
        self._fetch_status.setText("Fetching…")
        # Free the previous fetcher (finished — the button re-enables only on
        # done) so repeated fetches don't pile up dead QThread children.
        if self._fetcher is not None:
            self._fetcher.deleteLater()
        self._fetcher = TipFetcher([ticker], self)
        self._fetcher.tips_ready.connect(self._on_fetch_done)
        self._fetcher.fetch_error.connect(self._on_fetch_error)
        self._fetcher.start()

    def _on_fetch_done(self, data: dict) -> None:
        self._fetch_btn.setEnabled(True)
        ticker = self._ticker.text().strip().upper()
        info = data.get(ticker, {})
        parts = []
        if info.get("action"):
            idx = self._action.findText(info["action"])
            if idx >= 0:
                self._action.setCurrentIndex(idx)
            parts.append(f"consensus: {info['action']}")
        if info.get("target"):
            self._target.setValue(info["target"])
            parts.append(f"target: ${info['target']:,.2f}")
        if info.get("count"):
            parts.append(f"{info['count']} analysts")
        self._fetch_status.setText(", ".join(parts) if parts else "No analyst data found.")

    def done(self, result: int) -> None:
        # OK, Cancel, Esc, and the window-close button all funnel through done();
        # stop any in-flight analyst fetch so its QThread isn't destroyed while
        # still running when the dialog is torn down.
        stop_fetcher(self._fetcher)
        super().done(result)

    def _on_fetch_error(self, message: str) -> None:
        self._fetch_btn.setEnabled(True)
        self._fetch_status.setText(f"Error: {message[:60]}")

    def _on_accept(self) -> None:
        if normalize_ticker(self._ticker.text()) is None:
            self._fetch_status.setText("Enter a valid ticker (letters, digits, '.', '-').")
            self._ticker.setFocus()
            return
        self.accept()

    def tip(self) -> StockTip:
        target = cents(self._target.value()) or None
        return StockTip(
            id=self._tip.id if self._tip else 0,
            ticker=self._ticker.text().strip().upper(),
            action=self._action.currentText(),
            target_price=target,
            confidence=self._confidence.value(),
            notes=self._notes.toPlainText().strip() or None,
            added_date=self._tip.added_date if self._tip else date.today().isoformat(),
            analyst_action=self._tip.analyst_action if self._tip else None,
            analyst_target=self._tip.analyst_target if self._tip else None,
            analyst_count=self._tip.analyst_count if self._tip else None,
            analyst_updated=self._tip.analyst_updated if self._tip else None,
        )
