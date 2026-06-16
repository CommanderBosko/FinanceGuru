from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.categories import GOAL_NOTE
from financeguru.models.bill import Bill
from financeguru.models.goal import Goal, months_remaining
from financeguru.money import ZERO
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import payments as payment_repo
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.goal_dialog import GoalDialog

_COLS = ["Goal", "Price", "Amount Left", "Afford By", "Months Left", "Save / Month"]


class GoalsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._goals: list[Goal] = []

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Goal")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, len(_COLS))
        self._table.setHorizontalHeaderLabels(_COLS)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_edit.clicked.connect(self._on_edit)
        self._btn_delete.clicked.connect(self._on_delete)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        self._table.doubleClicked.connect(self._on_edit)

        attach_row_menu(self._table, [
            ("Add Goal", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def refresh(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        self._goals = goal_repo.get_all()
        paid = payment_repo.total_paid_by_bill()
        self._table.setRowCount(len(self._goals))
        for row, goal in enumerate(self._goals):
            def _right(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                return item

            def _center(text: str) -> QTableWidgetItem:
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            # Each Goal-bill payment chips away at what's left to fund the goal.
            contributed = paid.get(goal.bill_id, ZERO) if goal.bill_id else ZERO
            left = max(goal.price - contributed, ZERO)

            self._table.setItem(row, 0, QTableWidgetItem(goal.name))
            self._table.setItem(row, 1, _right(f"${goal.price:,.2f}"))
            self._table.setItem(row, 2, _right(f"${left:,.2f}"))
            self._table.setItem(row, 3, _center(goal.target_date))
            self._table.setItem(row, 4, _center(str(months_remaining(goal.target_date))))
            self._table.setItem(row, 5, _right(f"${goal.monthly_savings():,.2f}"))

    def _selected_goal(self) -> Goal | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        return self._goals[row]

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    # ── Bill sync ───────────────────────────────────────────────────────────
    # Each goal is mirrored by a recurring "Goal" bill so the monthly
    # contribution shows up alongside the rest of the budget in the Bills tab.

    def _bill_for_goal(self, goal: Goal) -> Bill:
        target = date.fromisoformat(goal.target_date)
        return Bill(
            id=goal.bill_id,
            name=goal.name,
            amount=goal.monthly_savings(),
            due_day=target.day,
            recurrence="monthly",
            is_active=True,
            notes=GOAL_NOTE,
        )

    def _on_add(self) -> None:
        dialog = GoalDialog(self)
        if not dialog.exec():
            return
        goal = dialog.goal()
        goal.bill_id = bill_repo.add(self._bill_for_goal(goal))
        goal_repo.add(goal)
        self._refresh()

    def _on_edit(self) -> None:
        goal = self._selected_goal()
        if goal is None:
            return
        dialog = GoalDialog(self, goal)
        if not dialog.exec():
            return
        updated = dialog.goal()
        bill = self._bill_for_goal(updated)
        if updated.bill_id is None:
            updated.bill_id = bill_repo.add(bill)
        else:
            bill_repo.update(bill)
        goal_repo.update(updated)
        self._refresh()

    def _on_delete(self) -> None:
        goal = self._selected_goal()
        if goal is None:
            return
        answer = QMessageBox.question(
            self, "Delete Goal",
            f"Delete \"{goal.name}\"? Its monthly Goal bill will also be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if goal.bill_id is not None:
            bill_repo.delete(goal.bill_id)
        goal_repo.delete(goal.id)
        self._refresh()
