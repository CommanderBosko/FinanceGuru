from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.categories import GOAL_NOTE, SAVINGS_CATEGORY
from financeguru.models.bill import Bill
from financeguru.models.goal import Goal, months_remaining
from financeguru.money import ZERO
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
from financeguru.repositories import payments as payment_repo
from financeguru.views._table import center, money, right
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.goal_dialog import GoalDialog

_COLS = ["Goal", "Price", "Amount Left", "Start Date", "Afford By", "Months Left", "Save / Month"]

MonthKey = tuple[int, int] | None


def _month_entries(goals: list[Goal]) -> list[tuple[str, MonthKey]]:
    """(label, (year, month)) pairs for the Goals tab's month picker.

    Unlike Bills' picker (which also has to account for one-time/yearly due
    months), a Goal has exactly one date that gates its visibility — its
    start_date, since a goal can't be shown before it exists — so the window
    is just the union of the current month and every goal's start_date month.
    Always includes the current month so the picker never starts empty on a
    fresh database. Sorted oldest-first, matching Bills' picker.
    """
    today = date.today()
    months = {(today.year, today.month)}
    for goal in goals:
        d = date.fromisoformat(goal.start_date)
        months.add((d.year, d.month))
    entries: list[tuple[str, MonthKey]] = [("All", None)]
    entries += [(date(y, m, 1).strftime("%B %Y"), (y, m)) for y, m in sorted(months)]
    return entries


def _visible_in_month(goal: Goal, key: MonthKey, paid_through: dict[int, Decimal]) -> bool:
    """Whether `goal` belongs on the Goals tab for the selected month.

    `key` of None is "All" — unfiltered, matching the tab's historical
    behavior. Otherwise a goal must (a) have already started by the selected
    month, and (b) still have a balance greater than zero as of the start of
    that month — i.e. what was paid toward its bill strictly before that
    month began hadn't yet covered its price. Condition (b) alone is enough
    to both surface a goal in the month it finishes (its balance-before was
    still positive even if a payment during the month fully funds it) and
    drop it the month after, so no separate "completion month" branch is
    needed. This is deliberately not the same rule as Bills' `_visible_in_month`
    for a goal's mirrored bill — Bills has no funded/unfunded cutoff, since a
    bill you still have doesn't stop being a bill just because its linked
    goal is paid off.
    """
    if key is None:
        return True
    year, month = key
    start_date = date.fromisoformat(goal.start_date)
    if (year, month) < (start_date.year, start_date.month):
        return False
    contributed = paid_through.get(goal.bill_id, ZERO) if goal.bill_id is not None else ZERO
    return goal.price - contributed > ZERO


class GoalsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._goals: list[Goal] = []
        # The currently filtered (year, month), or None for "All". Owned
        # locally so this view still works standalone (tests, qt-smoke);
        # under MainWindow it's driven by the global month selector via
        # select_month()/select_all() below. Defaults to "All", matching this
        # tab's pre-existing standalone default.
        self._current_key: MonthKey = None

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
        self._table.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._table.setSortingEnabled(True)
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

    def month_keys(self) -> list[tuple[int, int]]:
        """(year, month) keys this tab currently considers interesting.

        Used by MainWindow to build the global month selector's entry list
        as the union of every affected tab's own list — see `_month_entries`
        for the actual "interesting months" rule.
        """
        return [key for _, key in _month_entries(goal_repo.get_all()) if key is not None]

    def select_month(self, year: int, month: int, *, strict: bool = False) -> None:
        """Programmatically select `(year, month)` as the current filter.

        Used both by MainWindow's global month selector and by a Notes-tab
        link click landing on a goal's own start month. By default, falls
        back to "All" (None) if `(year, month)` isn't one of this tab's own
        populated entries (see `month_keys`) — cross-tab navigation needs the
        goal it's jumping to to always end up visible somewhere. Pass
        `strict=True` (used only by MainWindow's global broadcast) to select
        the literal month regardless — otherwise the toolbar could show a
        specific month while this tab silently falls back to showing every
        goal, a materially different, more misleading result than this tab's
        ordinary "no goal active yet" empty state for an uninteresting month.
        Always triggers a refresh, whether or not the key actually changed.
        """
        target = (year, month)
        self._current_key = target if strict or target in self.month_keys() else None
        self._refresh()

    def select_all(self) -> None:
        """Programmatically select "All" as the current filter."""
        self._current_key = None
        self._refresh()

    def _refresh(self) -> None:
        all_goals = goal_repo.get_all()

        key = self._current_key
        if key is None:
            # "All" — the full, current picture: every payment made to date.
            paid_through: dict[int, Decimal] = {}
            paid = payment_repo.total_paid_by_bill()
        else:
            # A specific month — "Amount Left" must reflect the balance as of
            # that month, the same paid_through figure _visible_in_month used
            # to decide the goal belongs here, not today's all-time total (or
            # a fully-funded goal would misleadingly show $0 left in a past
            # month it hadn't finished funding yet).
            year, month = key
            paid_through = payment_repo.total_paid_by_bill_through(f"{year:04d}-{month:02d}-01")
            paid = paid_through
        self._goals = [g for g in all_goals if _visible_in_month(g, key, paid_through)]

        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._goals))
        for row, goal in enumerate(self._goals):
            # Each Goal-bill payment chips away at what's left to fund the goal.
            contributed = paid.get(goal.bill_id, ZERO) if goal.bill_id else ZERO
            left = max(goal.price - contributed, ZERO)
            months_left = months_remaining(goal.target_date)
            monthly_savings = goal.monthly_savings()

            name_item = QTableWidgetItem(goal.name)
            name_item.setData(Qt.ItemDataRole.UserRole, goal)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, right(money(goal.price), float(goal.price)))
            self._table.setItem(row, 2, right(money(left), float(left)))
            self._table.setItem(row, 3, center(goal.start_date))
            self._table.setItem(row, 4, center(goal.target_date))
            self._table.setItem(row, 5, center(str(months_left), months_left))
            self._table.setItem(row, 6, right(money(monthly_savings), float(monthly_savings)))
        self._table.setSortingEnabled(True)

    def _selected_goal(self) -> Goal | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

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
            category=SAVINGS_CATEGORY,
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
        linked_notes = note_repo.get_by_goal_id(goal.id) if goal.id is not None else []
        if not linked_notes:
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
            return

        # Notes link to this goal — fold the choice into one dialog rather
        # than a second popup. "No" still deletes the goal; the notes' link
        # is left to the goal_id FK's ON DELETE SET NULL, which clears it.
        answer = QMessageBox.question(
            self, "Delete Goal",
            f"Delete \"{goal.name}\"? Its monthly Goal bill will also be removed.\n\n"
            f"{len(linked_notes)} note(s) are linked to this goal.\n\n"
            "Yes — delete the goal and those notes.\n"
            "No — delete the goal and keep the notes (their link will be cleared).\n"
            "Cancel — don't delete anything.",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if answer == QMessageBox.StandardButton.Cancel:
            return
        if goal.bill_id is not None:
            bill_repo.delete(goal.bill_id)
        goal_repo.delete(goal.id, delete_linked_notes=answer == QMessageBox.StandardButton.Yes)
        self._refresh()
