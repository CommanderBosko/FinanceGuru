from datetime import date

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QHeaderView, QMessageBox, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from financeguru.models.bill import Bill
from financeguru.models.note import Note
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo
from financeguru.repositories import notes as note_repo
from financeguru.views._month_filter import month_entries
from financeguru.views._table import center
from financeguru.views.context_menu import attach_row_menu
from financeguru.views.note_dialog import NoteDialog


def _bill_target_month(bill: Bill, today: date, goal_start: date | None = None) -> tuple[int, int]:
    """The month a note's linked Bill should navigate the Bills tab to.

    Monthly bills are always due, so "now" is as good a month as any — unless
    this bill is a Goal's mirrored bill (always monthly, per
    GoalsView._bill_for_goal) whose Goal hasn't started yet: BillsView's own
    goal-start gating would hide it in "now", so ``goal_start`` (when given)
    clamps the target forward to the goal's first visible month instead of
    landing on a month that's a dead end. Yearly bills use this year's
    occurrence if it hasn't passed yet, otherwise next year's — mirroring the
    same "hasn't passed" logic Bill.due_sort_key uses. One-time bills have
    exactly one possible month: their own (goal-mirrored bills are never
    yearly/one-time, so ``goal_start`` doesn't apply to these two branches).
    """
    if bill.recurrence == "yearly" and bill.due_month is not None:
        year = today.year if bill.due_month >= today.month else today.year + 1
        return (year, bill.due_month)
    if bill.recurrence == "one-time" and bill.due_year is not None and bill.due_month is not None:
        return (bill.due_year, bill.due_month)
    target = (today.year, today.month)
    if goal_start is not None:
        start = (goal_start.year, goal_start.month)
        if start > target:
            return start
    return target


class NotesView(QWidget):
    # Emitted when a note's link indicator is clicked: (target, year, month)
    # where target is "bills" or "goals" — MainWindow switches to that tab
    # and calls its select_month(year, month).
    navigate_requested = Signal(str, int, int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._notes: list[Note] = []
        # Notes has no "All" state — every note is always filed under exactly
        # one month — so this is always a concrete (year, month), never None.
        # Owned locally so this view still works standalone (tests,
        # qt-smoke); under MainWindow it's driven by the global month
        # selector via select_month() below, which — unlike every other
        # affected tab — deliberately has no select_all() counterpart: a
        # global "All" is simply never forwarded here (see MainWindow),
        # so Notes just keeps showing whichever specific month it was on.
        self._current_key: tuple[int, int] = (date.today().year, date.today().month)

        layout = QVBoxLayout(self)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add Note")
        self._btn_edit = QPushButton("Edit")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_edit)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["When", "Note", "Link"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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
            ("Add Note", self._on_add, False),
            None,
            ("Edit", self._on_edit, True),
            ("Delete", self._on_delete, True),
        ])

        self._refresh()

    def refresh(self) -> None:
        self._refresh()

    def month_keys(self) -> list[tuple[int, int]]:
        """(year, month) keys this tab currently considers interesting —
        every month from the earliest note on record through today.

        Used by MainWindow to build the global month selector's entries.
        """
        earliest = note_repo.earliest_month()
        # "YYYY-MM" -> "YYYY-MM-01" so month_entries' day-based parsing (it
        # slices [:4]/[5:7]) works the same as every other tab.
        earliest_date = f"{earliest}-01" if earliest else None
        return [key for _, key in month_entries(earliest_date, include_all=False)]

    def select_month(self, year: int, month: int) -> None:
        """Programmatically select `(year, month)` as the current filter.

        There is deliberately no select_all() counterpart — see the
        _current_key comment in __init__.
        """
        self._current_key = (year, month)
        self._refresh()

    def _refresh(self) -> None:
        year, month = self._current_key
        self._notes = note_repo.get_for_month(year, month)

        bills_by_id = {b.id: b for b in bill_repo.get_all() if b.id is not None}
        all_goals = goal_repo.get_all()
        goals_by_id = {g.id: g for g in all_goals if g.id is not None}
        # A goal's own auto-generated bill is always monthly (see
        # GoalsView._bill_for_goal) and shouldn't navigate to a month before
        # the goal starts — see _bill_target_month.
        goal_start_by_bill_id = {
            g.bill_id: date.fromisoformat(g.start_date)
            for g in all_goals if g.bill_id is not None
        }
        today = date.today()

        self._table.setRowCount(len(self._notes))
        for row, note in enumerate(self._notes):
            when_item = center(note.created_at.replace("T", " "))
            note_item = QTableWidgetItem(note.body.replace("\n", " "))
            note_item.setData(Qt.ItemDataRole.UserRole, note)
            note_item.setToolTip(note.body)
            self._table.setItem(row, 0, when_item)
            self._table.setItem(row, 1, note_item)
            self._table.setCellWidget(
                row, 2,
                self._link_widget(note, bills_by_id, goals_by_id, goal_start_by_bill_id, today),
            )

    def _link_widget(self, note: Note, bills_by_id: dict, goals_by_id: dict,
                      goal_start_by_bill_id: dict, today: date):
        if note.bill_id is not None:
            bill = bills_by_id.get(note.bill_id)
            if bill is None:
                return None
            btn = QPushButton(f"→ {bill.name}")
            btn.setFlat(True)
            goal_start = goal_start_by_bill_id.get(note.bill_id)
            year, month = _bill_target_month(bill, today, goal_start)
            btn.clicked.connect(lambda: self.navigate_requested.emit("bills", year, month))
            return btn
        if note.goal_id is not None:
            goal = goals_by_id.get(note.goal_id)
            if goal is None:
                return None
            btn = QPushButton(f"→ {goal.name}")
            btn.setFlat(True)
            start = date.fromisoformat(goal.start_date)
            btn.clicked.connect(
                lambda: self.navigate_requested.emit("goals", start.year, start.month)
            )
            return btn
        return None

    def _selected_note(self) -> Note | None:
        row = self._table.currentRow()
        if row < 0 or not self._table.selectedItems():
            return None
        item = self._table.item(row, 1)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_selection_changed(self) -> None:
        enabled = bool(self._table.selectedItems())
        for btn in (self._btn_edit, self._btn_delete):
            btn.setEnabled(enabled)

    def _current_month_year(self) -> str:
        year, month = self._current_key
        return f"{year:04d}-{month:02d}"

    def _on_add(self) -> None:
        dialog = NoteDialog(self, month_year=self._current_month_year())
        if dialog.exec():
            note_repo.add(dialog.note())
            self._refresh()

    def _on_edit(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        dialog = NoteDialog(self, note=note)
        if dialog.exec():
            note_repo.update(dialog.note())
            self._refresh()

    def _on_delete(self) -> None:
        note = self._selected_note()
        if note is None:
            return
        answer = QMessageBox.question(
            self, "Delete Note", "Delete this note?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            note_repo.delete(note.id)
            self._refresh()
