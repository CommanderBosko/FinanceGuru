from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMessageBox,
    QPushButton, QSlider, QSpinBox, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from financeguru.budget import SPECIFIC_DAYS, format_pay_days, monthly_bill, monthly_income
from financeguru.models.income import Income
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import expenses as expense_repo
from financeguru.repositories import incomes as income_repo
from financeguru.views._table import center, money, right
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.income_dialog import IncomeDialog

_COLS = ["Source", "Amount", "Frequency", "Monthly", "Notes"]
_GREEN = "#2d9e2d"
_RED = "#c0392b"
_BLUE = "#2980b9"


class SalaryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._incomes: list[Income] = []

        # ── Income controls + table ───────────────────────────────────────
        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Paycheck")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()

        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.setMaximumHeight(220)
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(True)

        # ── Monthly budget summary ────────────────────────────────────────
        budget_box = QGroupBox("Monthly Budget")
        budget_layout = QHBoxLayout(budget_box)
        self._lbl_income = QLabel()
        self._lbl_bills = QLabel()
        self._lbl_expenses = QLabel()
        self._lbl_extra = QLabel()
        for lbl in (self._lbl_income, self._lbl_bills, self._lbl_expenses, self._lbl_extra):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            budget_layout.addWidget(lbl)
        big = QFont()
        big.setPointSize(13)
        big.setBold(True)
        self._lbl_extra.setFont(big)

        # ── Savings visualizer ────────────────────────────────────────────
        savings_box = QGroupBox("Set Aside Savings")
        savings_layout = QVBoxLayout(savings_box)

        rate_bar = QHBoxLayout()
        rate_bar.addWidget(QLabel("Savings rate:"))
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(20)
        rate_bar.addWidget(self._slider)
        self._pct = QSpinBox()
        self._pct.setRange(0, 100)
        self._pct.setSuffix("%")
        self._pct.setValue(20)
        rate_bar.addWidget(self._pct)
        savings_layout.addLayout(rate_bar)

        # Proportional save-vs-spend bar
        self._bar = QHBoxLayout()
        self._bar.setSpacing(2)
        self._save_seg = QLabel()
        self._spend_seg = QLabel()
        for seg in (self._save_seg, self._spend_seg):
            seg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            seg.setMinimumHeight(44)
            seg.setAutoFillBackground(True)
            font = seg.font()
            font.setBold(True)
            seg.setFont(font)
            seg.setStyleSheet("color: white;")
        self._bar.addWidget(self._save_seg)
        self._bar.addWidget(self._spend_seg)
        savings_layout.addLayout(self._bar)

        self._savings_detail = QLabel()
        self._savings_detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        savings_layout.addWidget(self._savings_detail)

        # ── Assemble ──────────────────────────────────────────────────────
        root = QVBoxLayout(self)
        root.addLayout(btn_bar)
        root.addWidget(self._table)
        root.addWidget(budget_box)
        root.addWidget(savings_box)
        root.addStretch()

        # ── Connections ───────────────────────────────────────────────────
        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)
        attach_row_menu(self._table, [
            ("Add Paycheck", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])
        self._slider.valueChanged.connect(self._on_rate_changed)
        self._pct.valueChanged.connect(self._on_rate_changed)

        self.refresh()

    # ── Data ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._incomes = income_repo.get_all()
        self._render_table()
        self._recompute()

    def _render_table(self) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._incomes))
        for row, inc in enumerate(self._incomes):
            monthly = monthly_income(inc)
            name_item = QTableWidgetItem(inc.name)
            name_item.setData(Qt.ItemDataRole.UserRole, inc)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, right(money(inc.amount), float(inc.amount)))
            if inc.frequency == SPECIFIC_DAYS:
                days = format_pay_days(inc.pay_days)
                freq_text = f"days {days}" if days else SPECIFIC_DAYS
            else:
                freq_text = inc.frequency
            self._table.setItem(row, 2, center(freq_text))
            self._table.setItem(row, 3, right(money(monthly), float(monthly)))
            self._table.setItem(row, 4, QTableWidgetItem(inc.notes or ""))
        self._table.setSortingEnabled(True)

    def _recompute(self) -> None:
        total_income = sum(monthly_income(i) for i in self._incomes)
        total_bills = sum(monthly_bill(b) for b in bill_repo.get_all())
        # This month's logged one-off spending (Expenses tab), on top of the
        # recurring bill obligations, so "extra" is what's actually left to save.
        today = date.today()
        total_expenses = expense_repo.total_for_month(today.year, today.month)
        extra = total_income - total_bills - total_expenses

        self._lbl_income.setText(f"Monthly Income\n{money(total_income)}")
        self._lbl_bills.setText(f"Monthly Bills\n−{money(total_bills)}")
        self._lbl_expenses.setText(f"This Month's Expenses\n−{money(total_expenses)}")
        extra_color = _GREEN if extra >= 0 else _RED
        label = "Extra Spending Money" if extra >= 0 else "Over Budget"
        self._lbl_extra.setText(f"{label}\n{money(extra)}")
        self._lbl_extra.setStyleSheet(f"color: {extra_color};")

        self._update_savings(extra)

    def _update_savings(self, extra: Decimal) -> None:
        pct = self._slider.value()

        if extra <= 0:
            self._save_seg.setStyleSheet(f"background: {_RED}; color: white;")
            self._save_seg.setText("Nothing left to set aside")
            self._spend_seg.hide()
            self._bar.setStretch(0, 1)
            self._bar.setStretch(1, 0)
            self._savings_detail.setText(
                "Your bills meet or exceed your income — no spare money to save this month."
            )
            return

        self._spend_seg.show()
        save = extra * pct / 100
        spend = extra - save

        self._save_seg.setStyleSheet(f"background: {_GREEN}; color: white;")
        self._spend_seg.setStyleSheet(f"background: {_BLUE}; color: white;")
        self._save_seg.setText(f"Save ${save:,.0f}" if save else "")
        self._spend_seg.setText(f"Spend ${spend:,.0f}" if spend else "")
        self._bar.setStretch(0, max(0, round(save)))
        self._bar.setStretch(1, max(0, round(spend)))

        self._savings_detail.setText(
            f"Set aside {money(save)}/mo  ({money(save * 12)}/yr)"
            f"   ·   Free to spend {money(spend)}/mo"
        )

    # ── Slots ─────────────────────────────────────────────────────────────

    def _selected(self) -> Income | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _on_rate_changed(self, value: int) -> None:
        for widget in (self._slider, self._pct):
            if widget.value() != value:
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
        self._recompute()

    def _on_add(self) -> None:
        dialog = IncomeDialog(self)
        if dialog.exec():
            income_repo.add(dialog.income())
            self.refresh()

    def _on_edit(self) -> None:
        income = self._selected()
        if income is None:
            return
        dialog = IncomeDialog(self, income)
        if dialog.exec():
            income_repo.update(dialog.income())
            self.refresh()

    def _on_delete(self) -> None:
        income = self._selected()
        if income is None:
            return
        answer = QMessageBox.question(
            self, "Delete Paycheck",
            f"Delete \"{income.name}\"?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            income_repo.delete(income.id)
            self.refresh()
