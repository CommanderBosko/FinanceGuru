from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox, QFrame, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QSplitter, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.debt import Debt
from financeguru.repositories import debts as debt_repo
from financeguru.snowball import PayoffPlan, calculate, payoff_date
from financeguru.views.debt_dialog import DebtDialog

_COLS_DEBT = ["Name", "Balance", "APR %", "Min Payment", "Notes"]
_COLS_RESULT = ["#", "Debt", "Balance", "APR %", "Payoff Month", "Payoff Date", "Interest Paid"]


class DebtSnowballView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._debts: list[Debt] = []

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

        self._results_frame.setVisible(False)

        # ── Assemble ──────────────────────────────────────────────────────
        splitter = QSplitter(Qt.Orientation.Vertical)
        top = QWidget()
        top_layout = QVBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addLayout(btn_bar)
        top_layout.addWidget(self._debt_table)
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
        snowball, avalanche = calculate(self._debts, extra)
        self._fill_result_panel(self._snowball_box, snowball)
        self._fill_result_panel(self._avalanche_box, avalanche)
        self._fill_comparison(snowball, avalanche)
        self._results_frame.setVisible(True)

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
