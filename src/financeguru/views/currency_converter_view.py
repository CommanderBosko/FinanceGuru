import sys
import traceback
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

from financeguru.currencies import (
    CURRENCIES, DEFAULT_FROM, DEFAULT_TO, PIVOT_BASE, ZERO_DECIMAL_CURRENCIES,
)
from financeguru.models.currency_rates import CurrencyRates
from financeguru.money import cents
from financeguru.rates import RatesFetcher, stop_fetcher
from financeguru.repositories import currency_rates as rates_repo
from financeguru.repositories import preferences as prefs_repo

_PREF_FROM = "currency_converter.from"
_PREF_TO = "currency_converter.to"
_PREF_AMOUNT = "currency_converter.amount"

_DEFAULT_AMOUNT = Decimal("100.00")


class CurrencyConverterView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._rates: dict[str, Decimal] = {}
        self._rates_date: str = ""
        self._fetcher: RatesFetcher | None = None

        layout = QVBoxLayout(self)

        form = QHBoxLayout()
        self._amount = QDoubleSpinBox()
        self._amount.setRange(0.0, 999_999_999.99)
        self._amount.setDecimals(2)
        self._amount.setMinimumWidth(140)

        self._from_combo = QComboBox()
        self._to_combo = QComboBox()
        for combo in (self._from_combo, self._to_combo):
            for code, name in CURRENCIES:
                combo.addItem(name, code)

        self._swap_btn = QPushButton("⇄")
        self._swap_btn.setToolTip("Swap currencies")
        self._swap_btn.setFixedWidth(36)

        form.addWidget(QLabel("Amount"))
        form.addWidget(self._amount)
        form.addWidget(QLabel("From"))
        form.addWidget(self._from_combo, 1)
        form.addWidget(self._swap_btn)
        form.addWidget(QLabel("To"))
        form.addWidget(self._to_combo, 1)
        layout.addLayout(form)

        self._result = QLabel("—")
        result_font = self._result.font()
        result_font.setPointSize(result_font.pointSize() + 6)
        result_font.setBold(True)
        self._result.setFont(result_font)
        layout.addWidget(self._result)

        self._rate_label = QLabel("")
        self._rate_label.setStyleSheet("color: gray;")
        layout.addWidget(self._rate_label)

        status_bar = QHBoxLayout()
        self._status = QLabel("")
        self._status.setStyleSheet("color: gray;")
        self._refresh_btn = QPushButton("Refresh Rates")
        status_bar.addWidget(self._status, 1)
        status_bar.addWidget(self._refresh_btn)
        layout.addLayout(status_bar)

        layout.addStretch()

        # Populate from saved state and the on-disk rate cache before wiring
        # any signals, so restoring a preference doesn't immediately re-save
        # itself or recompute against an empty rate table.
        self._load_preferences()
        self._load_cached_rates()
        self._recompute()

        self._amount.valueChanged.connect(self._on_input_changed)
        self._from_combo.currentIndexChanged.connect(self._on_input_changed)
        self._to_combo.currentIndexChanged.connect(self._on_input_changed)
        self._swap_btn.clicked.connect(self._on_swap)
        self._refresh_btn.clicked.connect(lambda: self._fetch_rates(force=True))

        self._fetch_rates(force=False)

    # ---- preferences / cache ----

    def _load_preferences(self) -> None:
        # Block signals while loading: refresh() calls this with the widgets'
        # signals already connected, and without this, setting the From combo
        # fires _on_input_changed -> _save_preferences() before the To combo
        # and amount are updated -- persisting their still-stale values and
        # clobbering the very preferences this is meant to load.
        widgets = (self._from_combo, self._to_combo, self._amount)
        for widget in widgets:
            widget.blockSignals(True)
        try:
            self._set_combo_code(self._from_combo, prefs_repo.get(_PREF_FROM, DEFAULT_FROM), DEFAULT_FROM)
            self._set_combo_code(self._to_combo, prefs_repo.get(_PREF_TO, DEFAULT_TO), DEFAULT_TO)
            amount_str = prefs_repo.get(_PREF_AMOUNT)
            try:
                amount = Decimal(amount_str) if amount_str else _DEFAULT_AMOUNT
            except Exception:
                amount = _DEFAULT_AMOUNT
            self._amount.setValue(float(amount))
        finally:
            for widget in widgets:
                widget.blockSignals(False)

    @staticmethod
    def _set_combo_code(combo: QComboBox, code: str | None, default_code: str) -> None:
        # A stored code can miss (key never written) or simply no longer match
        # any entry (CURRENCIES edited since, or a hand-edited/corrupted row);
        # either way fall back to the caller's actual default, not whatever
        # happens to sit at index 0 (alphabetically "Baht (Thailand)").
        index = combo.findData(code) if code else -1
        if index < 0:
            index = combo.findData(default_code)
        combo.setCurrentIndex(index if index >= 0 else 0)

    def _save_preferences(self) -> None:
        from_code = self._from_combo.currentData()
        to_code = self._to_combo.currentData()
        if from_code is None or to_code is None:
            return  # combo not yet populated/selected; nothing sensible to persist
        prefs_repo.set_many({
            _PREF_FROM: from_code,
            _PREF_TO: to_code,
            _PREF_AMOUNT: str(cents(self._amount.value())),
        })

    def _load_cached_rates(self) -> None:
        cached = rates_repo.get_cached(PIVOT_BASE)
        if cached is not None:
            self._rates = cached.rates
            self._rates_date = cached.fetched_at
            self._status.setText(f"Rates as of {self._rates_date}")
        else:
            self._status.setText("Fetching latest rates…")

    # ---- fetch ----

    def _fetch_rates(self, force: bool) -> None:
        if self._fetcher is not None and self._fetcher.isRunning():
            return
        # Frankfurter publishes once a day; skip the network round-trip if
        # today's rates are already cached, unless the user explicitly asked.
        if not force and self._rates_date == date.today().isoformat():
            return
        if self._fetcher is not None:
            self._fetcher.deleteLater()
        self._status.setText("Fetching latest rates…")
        self._refresh_btn.setEnabled(False)
        fetcher = RatesFetcher(PIVOT_BASE, self)
        self._fetcher = fetcher
        fetcher.rates_ready.connect(self._on_rates_ready)
        fetcher.fetch_error.connect(self._on_fetch_error)
        fetcher.start()

    def _on_rates_ready(self, rates: dict, rate_date: str) -> None:
        # Re-enabled here (rather than on the fetcher's `finished` signal) so
        # the button's state follows the outcome we actually handle, not a
        # second QThread-level signal that success/error already implies.
        self._refresh_btn.setEnabled(True)
        self._rates = rates
        self._rates_date = rate_date or date.today().isoformat()
        try:
            rates_repo.save(CurrencyRates(PIVOT_BASE, self._rates, self._rates_date))
        except Exception:
            # Best-effort cache write: a fetch that succeeded should still
            # update the UI even if persisting it (disk full, locked file on
            # these multi-user machines) fails.
            traceback.print_exc(file=sys.stderr)
        self._status.setText(f"Rates as of {self._rates_date}")
        self._recompute()

    def _on_fetch_error(self, message: str) -> None:
        self._refresh_btn.setEnabled(True)
        if self._rates:
            self._status.setText(f"Offline — showing rates as of {self._rates_date}")
        else:
            self._status.setText(message)
            self._result.setText("—")
            self._rate_label.setText("")

    # ---- conversion ----

    def _on_input_changed(self) -> None:
        self._save_preferences()
        self._recompute()

    def _on_swap(self) -> None:
        from_index = self._from_combo.currentIndex()
        to_index = self._to_combo.currentIndex()
        # Block signals for both index changes so swapping fires exactly one
        # save+recompute cycle instead of two (one per combo, transiently with
        # from==to in between).
        self._from_combo.blockSignals(True)
        self._to_combo.blockSignals(True)
        self._from_combo.setCurrentIndex(to_index)
        self._to_combo.setCurrentIndex(from_index)
        self._from_combo.blockSignals(False)
        self._to_combo.blockSignals(False)
        self._on_input_changed()

    def _recompute(self) -> None:
        from_code = self._from_combo.currentData()
        to_code = self._to_combo.currentData()
        if not from_code or not to_code or from_code not in self._rates or to_code not in self._rates:
            self._result.setText("—")
            self._rate_label.setText("")
            return
        rate = self._rates[to_code] / self._rates[from_code]
        raw = Decimal(str(self._amount.value())) * rate
        if to_code in ZERO_DECIMAL_CURRENCIES:
            converted = raw.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
            self._result.setText(f"{converted:,.0f} {to_code}")
        else:
            self._result.setText(f"{cents(raw):,.2f} {to_code}")
        self._rate_label.setText(f"1 {from_code} = {rate.quantize(Decimal('0.0001'))} {to_code}")

    # ---- MainWindow contract ----

    def refresh(self) -> None:
        # DB-local only, matching the Stocks/Stock Tips convention (network
        # fetch is triggered by construction and the explicit Refresh Rates
        # button, not by refresh()) — and reloads preferences too, so a DB
        # restore's from/to/amount actually take effect instead of leaving
        # this tab showing pre-restore selections against post-restore data.
        self._load_preferences()
        self._load_cached_rates()
        self._recompute()

    def stop_threads(self) -> None:
        # Called by MainWindow.closeEvent on quit; this view is nested in a
        # QTabWidget and never receives its own close event.
        stop_fetcher(self._fetcher)
