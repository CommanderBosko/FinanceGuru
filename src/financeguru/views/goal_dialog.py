from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFormLayout, QLabel, QLineEdit, QMessageBox, QTextEdit, QVBoxLayout,
)

from financeguru.models.goal import Goal
from financeguru.money import cents


def _end_of_month(d: QDate) -> QDate:
    return QDate(d.year(), d.month(), d.daysInMonth())


class GoalDialog(QDialog):
    def __init__(self, parent=None, goal: Goal | None = None):
        super().__init__(parent)
        self._goal = goal
        self.setWindowTitle("Edit Goal" if goal else "Add Goal")
        self.setMinimumWidth(380)

        form = QFormLayout()

        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. New Laptop")
        form.addRow("Goal:", self._name)

        self._price = QDoubleSpinBox()
        self._price.setRange(0.01, 9_999_999)
        self._price.setDecimals(2)
        self._price.setPrefix("$")
        form.addRow("Price:", self._price)

        # A goal is always funded by month's end, so the picker chooses a
        # month and the day is snapped to the last day of that month.
        self._target = QDateEdit(_end_of_month(QDate.currentDate().addMonths(6)))
        self._target.setCalendarPopup(True)
        self._target.setDisplayFormat("MMMM yyyy")
        self._target.setMinimumDate(QDate.currentDate())
        form.addRow("Afford by:", self._target)

        self._monthly = QLabel()
        font = self._monthly.font()
        font.setBold(True)
        self._monthly.setFont(font)
        form.addRow("Save monthly:", self._monthly)

        self._notes = QTextEdit()
        self._notes.setFixedHeight(60)
        form.addRow("Notes:", self._notes)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        self._price.valueChanged.connect(self._update_monthly)
        self._target.dateChanged.connect(self._update_monthly)

        if goal:
            self._name.setText(goal.name)
            self._price.setValue(float(goal.price))
            self._target.setDate(QDate.fromString(goal.target_date, "yyyy-MM-dd"))
            self._notes.setPlainText(goal.notes or "")
        self._update_monthly()

    def _update_monthly(self) -> None:
        monthly = self._build_goal().monthly_savings()
        self._monthly.setText(f"${monthly:,.2f} / month")

    def _build_goal(self) -> Goal:
        return Goal(
            id=self._goal.id if self._goal else None,
            name=self._name.text().strip(),
            price=cents(self._price.value()),
            target_date=_end_of_month(self._target.date()).toString("yyyy-MM-dd"),
            notes=self._notes.toPlainText().strip() or None,
            bill_id=self._goal.bill_id if self._goal else None,
        )

    def _on_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.information(self, "Name Required", "Give the goal a name.")
            self._name.setFocus()
            return
        self.accept()

    def goal(self) -> Goal:
        return self._build_goal()
