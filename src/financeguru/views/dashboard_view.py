from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.money import ZERO
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import payments as payment_repo

_GREEN = QColor("#2d9e2d")
_RED = QColor("#c0392b")
_ORANGE = QColor("#d35400")


class DashboardView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self._month_label = QLabel()
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self._month_label.setFont(font)
        layout.addWidget(self._month_label)

        bills_group = QGroupBox("Bills This Month")
        bills_layout = QVBoxLayout(bills_group)
        self._bills_table = QTableWidget(0, 4)
        self._bills_table.setHorizontalHeaderLabels(["Name", "Amount", "Due Day", "Status"])
        self._bills_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._bills_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._bills_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._bills_table.setAlternatingRowColors(True)
        self._bills_table.verticalHeader().setVisible(False)
        bills_layout.addWidget(self._bills_table)
        layout.addWidget(bills_group)

        summary_group = QGroupBox("Summary")
        summary_layout = QHBoxLayout(summary_group)
        self._lbl_total = QLabel()
        self._lbl_paid = QLabel()
        self._lbl_remaining = QLabel()
        for lbl in (self._lbl_total, self._lbl_paid, self._lbl_remaining):
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            summary_layout.addWidget(lbl)
        layout.addWidget(summary_group)

        self.refresh()

    def refresh(self) -> None:
        today = date.today()
        paid_ids = payment_repo.get_paid_bill_ids_for_month(today.year, today.month)
        # Monthly bills are due every month; yearly bills in their due_month;
        # one-time bills only in their exact due_year/due_month (see
        # Bill.is_due_in).
        active = [b for b in bill_repo.get_all() if b.is_active]
        bills = [b for b in active if b.is_due_in(today.year, today.month)]

        # Carried-over rows: yearly/one-time bills whose most recent due
        # cycle passed unpaid (see Bill.overdue_carryover_start).
        latest_paid = payment_repo.latest_paid_dates()
        carried = []
        for b in active:
            cycle_start = b.overdue_carryover_start(today.year, today.month)
            if cycle_start is None:
                continue
            if b.recurrence == "one-time":
                # One-time bills are paid once — any payment ever (even one
                # made early) settles them.
                unpaid = b.id not in latest_paid
            else:
                # Yearly: a payment from a previous year's cycle must not
                # satisfy this year's, so require one on/after cycle start.
                unpaid = latest_paid.get(b.id, "") < cycle_start
            if unpaid:
                carried.append((b, cycle_start))

        self._month_label.setText(today.strftime("%B %Y"))
        self._bills_table.setRowCount(len(bills) + len(carried))

        total = ZERO
        paid = ZERO

        for row, bill in enumerate(bills):
            is_paid = bill.id in paid_ids
            is_overdue = not is_paid and bill.due_day < today.day

            if is_paid:
                status = "Paid ✓"
                color = _GREEN
            elif is_overdue:
                status = "Overdue"
                color = _RED
            else:
                status = f"Due on {bill.due_day}"
                color = _ORANGE if bill.due_day == today.day else None

            amount_item = QTableWidgetItem(f"${bill.amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            due_item = QTableWidgetItem(str(bill.due_day))
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item = QTableWidgetItem(status)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            if color:
                for item in (amount_item, due_item, status_item):
                    item.setForeground(color)

            self._bills_table.setItem(row, 0, QTableWidgetItem(bill.name))
            self._bills_table.setItem(row, 1, amount_item)
            self._bills_table.setItem(row, 2, due_item)
            self._bills_table.setItem(row, 3, status_item)

            total += bill.amount
            if is_paid:
                paid += bill.amount

        for offset, (bill, cycle_start) in enumerate(carried):
            row = len(bills) + offset
            month_abbr = date(int(cycle_start[:4]), int(cycle_start[5:7]), 1).strftime("%b")

            amount_item = QTableWidgetItem(f"${bill.amount:,.2f}")
            amount_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            due_item = QTableWidgetItem(f"{month_abbr} {bill.due_day}")
            due_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            status_item = QTableWidgetItem(f"Overdue ({month_abbr})")
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            for item in (amount_item, due_item, status_item):
                item.setForeground(_RED)

            self._bills_table.setItem(row, 0, QTableWidgetItem(bill.name))
            self._bills_table.setItem(row, 1, amount_item)
            self._bills_table.setItem(row, 2, due_item)
            self._bills_table.setItem(row, 3, status_item)

            total += bill.amount

        remaining = total - paid
        self._lbl_total.setText(f"Total Bills\n${total:,.2f}")
        self._lbl_paid.setText(f"Paid\n${paid:,.2f}")
        self._lbl_remaining.setText(f"Remaining\n${remaining:,.2f}")
