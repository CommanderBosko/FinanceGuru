from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.bill import Bill
from financeguru.models.goal import Goal
from financeguru.models.payment import Payment
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
from financeguru.repositories import payments as payment_repo
from financeguru.views.bill_dialog import BillDialog
from financeguru.views.context_menu import attach_row_menu
from financeguru.views._table import center, money, right

MonthKey = tuple[int, int] | None


def _month_entries(bills: list[Bill], goals: list[Goal]) -> list[tuple[str, MonthKey]]:
    """(label, (year, month)) pairs for the Bills tab's month picker.

    Unlike Payments/Income's picker (built from real dated log entries),
    Bills are recurring templates with no single date, so the window is
    assembled from whichever months are actually "interesting": the current
    month, every one-time bill's exact due month, this year's and next
    year's occurrence of every yearly bill's due month, and every goal's
    start/target month (the span its linked Goal bill can appear or
    disappear across). Always includes the current month so the picker
    never starts empty on a fresh database.

    Sorted oldest-first, unlike Payments/Income's newest-first picker —
    this one routinely spans both past and future months (a yearly bill's
    next occurrence, a goal's future start date), so chronological order
    reads better than a log-style "most recent first" list.
    """
    today = date.today()
    months = {(today.year, today.month)}
    for bill in bills:
        if bill.recurrence == "one-time" and bill.due_year is not None and bill.due_month is not None:
            months.add((bill.due_year, bill.due_month))
        elif bill.recurrence == "yearly" and bill.due_month is not None:
            months.add((today.year, bill.due_month))
            months.add((today.year + 1, bill.due_month))
    for goal in goals:
        for iso in (goal.start_date, goal.target_date):
            d = date.fromisoformat(iso)
            months.add((d.year, d.month))
    entries: list[tuple[str, MonthKey]] = [("All", None)]
    entries += [(date(y, m, 1).strftime("%B %Y"), (y, m)) for y, m in sorted(months)]
    return entries


def _visible_in_month(bill: Bill, key: MonthKey, goal_starts: dict[int, str]) -> bool:
    """Whether `bill` belongs on the Bills tab for the selected month.

    `key` of None is "All" — unfiltered, matching the tab's historical
    behavior. Otherwise this defers to `Bill.is_due_in` for ordinary
    recurrence, plus a goal-specific gate: a goal's linked bill shouldn't
    appear before the month its Goal's start_date falls in, something
    `is_due_in` can't know since start_date lives on the Goal, not the Bill.
    """
    if key is None:
        return True
    year, month = key
    if not bill.is_due_in(year, month):
        return False
    start_iso = goal_starts.get(bill.id) if bill.id is not None else None
    if start_iso:
        start_date = date.fromisoformat(start_iso)
        if (year, month) < (start_date.year, start_date.month):
            return False
    return True


class BillsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._bills: list[Bill] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Bill")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        self._btn_pay = QPushButton("Mark Paid")
        for btn in (self._btn_edit, self._btn_delete, self._btn_pay):
            btn.setEnabled(False)
        self._month_picker = QComboBox()
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addWidget(self._btn_pay)
        btn_bar.addWidget(self._month_picker)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 5)
        self._table.setHorizontalHeaderLabels(["Name", "Amount", "Due Day", "Recurrence", "Active"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(True)
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._btn_pay.clicked.connect(self._on_pay)
        self._month_picker.currentIndexChanged.connect(self._refresh)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Bill", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Mark Paid", self._on_pay, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def refresh(self) -> None:
        self._refresh()

    def select_month(self, year: int, month: int) -> None:
        """Programmatically select (year, month) in the month picker.

        Used by a Notes-tab link click to land on the bill's own due month.
        Matches by the (year, month) tuple stored as each combo item's data.
        Falls back to "All" (index 0) if that exact month isn't one of this
        picker's populated entries, so the caller is never left on a dead
        selection. Always triggers exactly one refresh — mirrors GoalsView's
        select_month so the two don't drift on this mechanic.
        """
        target = (year, month)
        index = 0
        for i in range(self._month_picker.count()):
            if self._month_picker.itemData(i) == target:
                index = i
                break
        self._month_picker.blockSignals(True)
        self._month_picker.setCurrentIndex(index)
        self._month_picker.blockSignals(False)
        self._refresh()

    def _refresh(self) -> None:
        all_bills = bill_repo.get_all()
        goals = goal_repo.get_all()
        goal_starts = {g.bill_id: g.start_date for g in goals if g.bill_id is not None}

        previous = self._month_picker.currentText()
        entries = _month_entries(all_bills, goals)
        labels = [label for label, _ in entries]
        self._month_picker.blockSignals(True)
        self._month_picker.clear()
        for label, key in entries:
            self._month_picker.addItem(label, key)
        if previous in labels:
            self._month_picker.setCurrentIndex(labels.index(previous))
        else:
            # First population, or the prior selection vanished — default to
            # the current month rather than "All".
            current_label = date.today().strftime("%B %Y")
            self._month_picker.setCurrentIndex(
                labels.index(current_label) if current_label in labels else 0
            )
        self._month_picker.blockSignals(False)

        key = self._month_picker.currentData()
        self._bills = [b for b in all_bills if _visible_in_month(b, key, goal_starts)]

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._bills))
        for row, bill in enumerate(self._bills):
            amount_item = right(money(bill.amount), float(bill.amount))
            due_item = center(str(bill.due_day), bill.due_day)
            name_item = QTableWidgetItem(bill.name)
            name_item.setData(Qt.ItemDataRole.UserRole, bill)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, amount_item)
            self._table.setItem(row, 2, due_item)
            self._table.setItem(row, 3, QTableWidgetItem(bill.recurrence.capitalize()))
            self._table.setItem(row, 4, QTableWidgetItem("Yes" if bill.is_active else "No"))
        self._table.setSortingEnabled(True)

    def _selected_bill(self) -> Bill | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete, self._btn_pay):
            btn.setEnabled(enabled)

    def _on_add(self) -> None:
        dialog = BillDialog(self)
        if dialog.exec():
            bill_repo.add(dialog.bill())
            self._refresh()

    def _on_edit(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        dialog = BillDialog(self, bill)
        if dialog.exec():
            bill_repo.update(dialog.bill())
            self._refresh()

    def _on_delete(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        linked_notes = note_repo.get_by_bill_id(bill.id) if bill.id is not None else []
        if not linked_notes:
            answer = QMessageBox.question(
                self,
                "Delete Bill",
                f"Delete '{bill.name}'? All associated payments will also be removed.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                bill_repo.delete(bill.id)
                self._refresh()
            return

        # Notes link to this bill — fold the choice into one dialog rather
        # than a second popup. "No" still deletes the bill; the notes' link
        # is left to the bill_id FK's ON DELETE SET NULL, which clears it.
        answer = QMessageBox.question(
            self,
            "Delete Bill",
            f"Delete '{bill.name}'? All associated payments will also be removed.\n\n"
            f"{len(linked_notes)} note(s) are linked to this bill.\n\n"
            "Yes — delete the bill and those notes.\n"
            "No — delete the bill and keep the notes (their link will be cleared).\n"
            "Cancel — don't delete anything.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return
        bill_repo.delete(bill.id, delete_linked_notes=answer == QMessageBox.StandardButton.Yes)
        self._refresh()

    def _on_pay(self) -> None:
        bill = self._selected_bill()
        if bill is None:
            return
        payment_repo.add(Payment(
            bill_id=bill.id,
            amount=bill.amount,
            paid_date=date.today().isoformat(),
        ))
        QMessageBox.information(
            self, "Payment Recorded",
            f"'{bill.name}' marked as paid on {date.today().strftime('%B %d, %Y')}."
        )
