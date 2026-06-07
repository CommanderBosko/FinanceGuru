from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.debt import Debt
from financeguru.repositories import debts as debt_repo
from financeguru.snowball import PayoffPlan, calculate, payoff_date
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.debt_dialog import DebtDialog

_COLS_DEBT = ["Name", "Balance", "APR %", "Min Payment", "Notes"]
_COLS_RESULT = ["#", "Debt", "Balance", "APR %", "Payoff Month", "Payoff Date", "Interest Paid"]
_COLS_LUMP = ["Month", "Date", "Amount"]
_MAX_MONTHS = 600  # 50-year cap, matches snowball simulation limit


class DebtSnowballView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._debts: list[Debt] = []
        self._plans: dict[str, PayoffPlan] = {}
        self._lump_sums: list[tuple[int, float]] = []  # (month, amount)

        # ── Top controls ──────────────────────────────────────────────────
        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Debt")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()

        extra_label = QLabel("Extra monthly payment:")
        self._extra = QDoubleSpinBox()
        self._extra.setRange(0, 99_999)
        self._extra.setDecimals(2)
        self._extra.setPrefix("$")
        self._extra.setValue(0)
        self._btn_calc = QPushButton("Calculate")
        btn_bar.addWidget(extra_label)
        btn_bar.addWidget(self._extra)
        btn_bar.addWidget(self._btn_calc)

        # ── Debt table ────────────────────────────────────────────────────
        self._debt_table = QTableWidget(0, len(_COLS_DEBT))
        self._debt_table.setHorizontalHeaderLabels(_COLS_DEBT)
        self._debt_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._debt_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._debt_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._debt_table.setAlternatingRowColors(True)
        self._debt_table.setMaximumHeight(200)

        # ── One-time extra payments ───────────────────────────────────────
        self._lump_box = QGroupBox("One-time extra payments  (e.g. tax refund, bonus)")
        lump_layout = QVBoxLayout(self._lump_box)

        entry = QHBoxLayout()
        entry.addWidget(QLabel("Month:"))
        self._lump_month = QSpinBox()
        self._lump_month.setRange(1, _MAX_MONTHS)
        self._lump_month.setPrefix("Month ")
        entry.addWidget(self._lump_month)
        self._lump_date = QLabel()
        self._lump_date.setStyleSheet("color: gray;")
        entry.addWidget(self._lump_date)
        entry.addSpacing(12)
        entry.addWidget(QLabel("Amount:"))
        self._lump_amount = QDoubleSpinBox()
        self._lump_amount.setRange(0, 9_999_999)
        self._lump_amount.setDecimals(2)
        self._lump_amount.setPrefix("$")
        entry.addWidget(self._lump_amount)
        self._btn_add_lump = QPushButton("Add")
        entry.addWidget(self._btn_add_lump)
        entry.addStretch()
        lump_layout.addLayout(entry)

        self._lump_table = QTableWidget(0, len(_COLS_LUMP))
        self._lump_table.setHorizontalHeaderLabels(_COLS_LUMP)
        self._lump_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self._lump_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._lump_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._lump_table.setAlternatingRowColors(True)
        self._lump_table.setMaximumHeight(140)
        lump_layout.addWidget(self._lump_table)

        self._btn_remove_lump = QPushButton("Remove Selected")
        self._btn_remove_lump.setEnabled(False)
        lump_layout.addWidget(self._btn_remove_lump, alignment=Qt.AlignmentFlag.AlignRight)

        # ── Results area ──────────────────────────────────────────────────
        self._results_frame = QFrame()
        results_layout = QVBoxLayout(self._results_frame)
        results_layout.setContentsMargins(0, 0, 0, 0)

        panels = QHBoxLayout()
        self._snowball_box = self._make_result_panel("❄ Snowball  (smallest balance first)")
        self._avalanche_box = self._make_result_panel("🌊 Avalanche  (highest rate first)")
        panels.addWidget(self._snowball_box)
        panels.addWidget(self._avalanche_box)
        results_layout.addLayout(panels)

        self._comparison = QLabel()
        self._comparison.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self._comparison.font()
        font.setBold(True)
        self._comparison.setFont(font)
        results_layout.addWidget(self._comparison)

        # ── Payment schedule ──────────────────────────────────────────────
        schedule_box = QGroupBox("Payment Schedule")
        schedule_layout = QVBoxLayout(schedule_box)
        selector_bar = QHBoxLayout()
        selector_bar.addWidget(QLabel("Strategy:"))
        self._schedule_strategy = QComboBox()
        self._schedule_strategy.addItems(["Snowball", "Avalanche"])
        selector_bar.addWidget(self._schedule_strategy)
        selector_bar.addStretch()
        schedule_layout.addLayout(selector_bar)
        self._schedule_table = QTableWidget(0, 0)
        self._schedule_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._schedule_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._schedule_table.setAlternatingRowColors(True)
        schedule_layout.addWidget(self._schedule_table)
        results_layout.addWidget(schedule_box)

        self._results_frame.setVisible(False)

        # ── Assemble ──────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addLayout(btn_bar)
        top_layout.addWidget(self._debt_table)
        top_layout.addWidget(self._lump_box)
        splitter.addWidget(top)
        splitter.addWidget(self._results_frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        root = QVBoxLayout(self)
        root.addWidget(splitter)

        # ── Connections ───────────────────────────────────────────────────
        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_calc.clicked.connect(self._on_calculate)
        self._debt_table.itemSelectionChanged.connect(self._on_selection_changed)
        self._debt_table.doubleClicked.connect(self._on_edit)
        attach_row_menu(self._debt_table, [
            ("Add Debt", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])
        attach_row_menu(self._lump_table, [
            ("Remove Selected", self._on_remove_lump, True),
        ])
        self._schedule_strategy.currentTextChanged.connect(self._render_schedule)
        self._btn_add_lump.clicked.connect(self._on_add_lump)
        self._btn_remove_lump.clicked.connect(self._on_remove_lump)
        self._lump_month.valueChanged.connect(self._update_lump_date)
        self._lump_table.itemSelectionChanged.connect(self._on_lump_selection_changed)

        self._update_lump_date()
        self._load()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _make_result_panel(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        table = QTableWidget(0, len(_COLS_RESULT))
        table.setHorizontalHeaderLabels(_COLS_RESULT)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        summary = QLabel()
        summary.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(table)
        layout.addWidget(summary)
        box.setProperty("_table", table)
        box.setProperty("_summary", summary)
        return box

    def _result_table(self, box: QGroupBox) -> QTableWidget:
        return box.property("_table")

    def _result_summary(self, box: QGroupBox) -> QLabel:
        return box.property("_summary")

    # ── Data ──────────────────────────────────────────────────────────────

    def _load(self) -> None:
        self._debts = debt_repo.get_all()
        self._render_debt_table()

    def _render_debt_table(self) -> None:
        self._debt_table.setRowCount(len(self._debts))
        for row, debt in enumerate(self._debts):
            def _right(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                return item

            self._debt_table.setItem(row, 0, QTableWidgetItem(debt.name))
            self._debt_table.setItem(row, 1, _right(f"${debt.balance:,.2f}"))
            self._debt_table.setItem(row, 2, _right(f"{debt.interest_rate:.2f}%"))
            self._debt_table.setItem(row, 3, _right(f"${debt.minimum_payment:,.2f}"))
            self._debt_table.setItem(row, 4, QTableWidgetItem(debt.notes or ""))

    def _selected_debt(self) -> Debt | None:
        row = self._debt_table.currentRow()
        if row < 0 or not self._debt_table.selectedItems():
            return None
        return self._debts[row]

    # ── Slots ─────────────────────────────────────────────────────────────

    def _on_selection_changed(self) -> None:
        enabled = bool(self._debt_table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    # ── One-time payments ───────────────────────────────────────────────────

    def _update_lump_date(self) -> None:
        self._lump_date.setText(f"({payoff_date(self._lump_month.value())})")

    def _on_add_lump(self) -> None:
        amount = self._lump_amount.value()
        if amount <= 0:
            QMessageBox.information(self, "No Amount", "Enter an amount greater than $0.")
            return
        self._lump_sums.append((self._lump_month.value(), amount))
        self._lump_sums.sort(key=lambda ls: ls[0])
        self._lump_amount.setValue(0)
        self._render_lump_table()

    def _on_remove_lump(self) -> None:
        row = self._lump_table.currentRow()
        if 0 <= row < len(self._lump_sums):
            del self._lump_sums[row]
            self._render_lump_table()

    def _on_lump_selection_changed(self) -> None:
        self._btn_remove_lump.setEnabled(bool(self._lump_table.selectedItems()))

    def _render_lump_table(self) -> None:
        self._lump_table.setRowCount(len(self._lump_sums))
        for row, (month, amount) in enumerate(self._lump_sums):
            month_item = QTableWidgetItem(f"Month {month}")
            month_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item = QTableWidgetItem(payoff_date(month))
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            amount_item = QTableWidgetItem(f"${amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._lump_table.setItem(row, 0, month_item)
            self._lump_table.setItem(row, 1, date_item)
            self._lump_table.setItem(row, 2, amount_item)

    def _on_add(self) -> None:
        dialog = DebtDialog(self)
        if dialog.exec():
            debt_repo.add(dialog.debt())
            self._load()

    def _on_edit(self) -> None:
        debt = self._selected_debt()
        if debt is None:
            return
        dialog = DebtDialog(self, debt)
        if dialog.exec():
            debt_repo.update(dialog.debt())
            self._load()

    def _on_delete(self) -> None:
        debt = self._selected_debt()
        if debt is None:
            return
        answer = QMessageBox.question(
            self, "Delete Debt",
            f"Delete \"{debt.name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            debt_repo.delete(debt.id)
            self._load()

    def _on_calculate(self) -> None:
        if not self._debts:
            QMessageBox.information(self, "No Debts", "Add at least one debt to calculate.")
            return
        extra = self._extra.value()
        snowball, avalanche = calculate(self._debts, extra, self._lump_sums)
        self._fill_result_panel(self._snowball_box, snowball)
        self._fill_result_panel(self._avalanche_box, avalanche)
        self._fill_comparison(snowball, avalanche)
        self._plans = {"Snowball": snowball, "Avalanche": avalanche}
        self._render_schedule()
        self._results_frame.setVisible(True)

    def _render_schedule(self) -> None:
        plan = self._plans.get(self._schedule_strategy.currentText())
        table = self._schedule_table
        if plan is None or not plan.schedule:
            table.setRowCount(0)
            table.setColumnCount(0)
            return

        headers = ["Month", "Date", *plan.debt_order, "Total"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(plan.schedule))

        def _right(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            return item

        def _center(text: str) -> QTableWidgetItem:
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            return item

        for row, m in enumerate(plan.schedule):
            table.setItem(row, 0, _center(str(m.month)))
            table.setItem(row, 1, _center(payoff_date(m.month)))
            for col, amount in enumerate(m.payments):
                text = f"${amount:,.2f}" if amount > 0 else "—"
                table.setItem(row, 2 + col, _right(text))
            table.setItem(row, len(headers) - 1, _right(f"${m.total:,.2f}"))

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)

    def _fill_result_panel(self, box: QGroupBox, plan: PayoffPlan) -> None:
        table = self._result_table(box)
        summary = self._result_summary(box)
        table.setRowCount(len(plan.debt_results))

        for row, r in enumerate(plan.debt_results):
            def _right(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                return item

            def _center(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            table.setItem(row, 0, _center(str(row + 1)))
            table.setItem(row, 1, QTableWidgetItem(r.name))
            table.setItem(row, 2, _right(f"${r.original_balance:,.2f}"))
            table.setItem(row, 3, _right(f"{r.apr:.2f}%"))
            table.setItem(row, 4, _center(f"Month {r.payoff_month}"))
            table.setItem(row, 5, _center(payoff_date(r.payoff_month)))
            table.setItem(row, 6, _right(f"${r.interest_paid:,.2f}"))

        yrs, mos = divmod(plan.total_months, 12)
        duration = f"{yrs}y {mos}m" if yrs else f"{mos}m"
        debt_free = payoff_date(plan.total_months)
        cap_note = "  ⚠ 50-year cap reached" if plan.capped else ""
        summary.setText(
            f"Debt-free: {debt_free}  ({duration})   |   "
            f"Total interest: ${plan.total_interest:,.2f}{cap_note}"
        )

    def _fill_comparison(self, snowball: PayoffPlan, avalanche: PayoffPlan) -> None:
        int_diff = snowball.total_interest - avalanche.total_interest
        mo_diff = snowball.total_months - avalanche.total_months

        if abs(int_diff) < 1 and mo_diff == 0:
            self._comparison.setText("Both strategies pay off your debt at the same time for the same total cost.")
            return

        if int_diff > 0:
            winner, loser = "Avalanche", "Snowball"
            saved = int_diff
            months = mo_diff
        else:
            winner, loser = "Snowball", "Avalanche"
            saved = -int_diff
            months = -mo_diff

        parts = [f"{winner} saves ${saved:,.2f} in interest vs {loser}"]
        if months > 0:
            yrs, mos = divmod(months, 12)
            time_str = f"{yrs}y {mos}m" if yrs else f"{mos} month{'s' if mos != 1 else ''}"
            parts.append(f"and pays off {time_str} sooner")
        self._comparison.setText("  ·  ".join(parts))
