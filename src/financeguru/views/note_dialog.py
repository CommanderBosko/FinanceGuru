from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QMessageBox, QTextEdit,
    QVBoxLayout,
)

from financeguru.models.note import Note
from financeguru.repositories import bills as bill_repo
from financeguru.repositories import goals as goal_repo

_LINK_NONE = "None"
_LINK_BILL = "Bill"
_LINK_GOAL = "Goal"


class NoteDialog(QDialog):
    def __init__(self, parent=None, month_year: str = "", note: Note | None = None):
        super().__init__(parent)
        self._note_id = note.id if note else None
        # Preserved as-is on edit — a note's timestamp reflects when it was
        # originally written, not when it was last edited.
        self._created_at = note.created_at if note else None
        # The month this note is filed under isn't editable here — it comes
        # from whichever month was selected in NotesView's picker when the
        # dialog was opened (both for a new note and when editing one).
        self._month_year = note.month_year if note else month_year
        self.setWindowTitle("Edit Note" if note else "Add Note")
        self.setMinimumWidth(400)

        self._form = form = QFormLayout()

        self._body = QTextEdit(note.body if note else "")
        self._body.setMinimumHeight(120)
        form.addRow("Note", self._body)

        # Read live at dialog-open time (not import time) so a bill/goal added
        # since the app started still shows up in the target picker.
        self._bills = bill_repo.get_all()
        self._goals = goal_repo.get_all()

        self._link_type = QComboBox()
        self._link_type.addItems([_LINK_NONE, _LINK_BILL, _LINK_GOAL])
        form.addRow("Link to", self._link_type)

        self._target = QComboBox()
        form.addRow("Target", self._target)

        self._link_type.currentTextChanged.connect(self._on_link_type_changed)

        if note and note.bill_id is not None:
            self._link_type.setCurrentText(_LINK_BILL)
        elif note and note.goal_id is not None:
            self._link_type.setCurrentText(_LINK_GOAL)
        else:
            self._on_link_type_changed(_LINK_NONE)
        if note and note.bill_id is not None:
            idx = self._target.findData(note.bill_id)
            if idx >= 0:
                self._target.setCurrentIndex(idx)
        elif note and note.goal_id is not None:
            idx = self._target.findData(note.goal_id)
            if idx >= 0:
                self._target.setCurrentIndex(idx)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _on_link_type_changed(self, link_type: str) -> None:
        self._target.clear()
        self._form.setRowVisible(self._target, link_type != _LINK_NONE)
        if link_type == _LINK_BILL:
            for bill in self._bills:
                self._target.addItem(bill.name, bill.id)
        elif link_type == _LINK_GOAL:
            for goal in self._goals:
                self._target.addItem(goal.name, goal.id)

    def _on_accept(self) -> None:
        if not self._body.toPlainText().strip():
            QMessageBox.information(self, "Note Required", "Write something in the note.")
            self._body.setFocus()
            return
        link_type = self._link_type.currentText()
        if link_type != _LINK_NONE and self._target.count() == 0:
            QMessageBox.information(
                self, "Nothing to Link",
                f"There are no {link_type.lower()}s yet to link this note to.",
            )
            return
        self.accept()

    def note(self) -> Note:
        link_type = self._link_type.currentText()
        bill_id = self._target.currentData() if link_type == _LINK_BILL else None
        goal_id = self._target.currentData() if link_type == _LINK_GOAL else None
        note = Note(
            id=self._note_id,
            body=self._body.toPlainText().strip(),
            month_year=self._month_year,
            bill_id=bill_id,
            goal_id=goal_id,
        )
        if self._created_at is not None:
            # Editing an existing note — keep its original timestamp instead
            # of the fresh one Note()'s default_factory just generated.
            note.created_at = self._created_at
        return note
