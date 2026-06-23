from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHBoxLayout, QInputDialog,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from financeguru.models.category import Category
from financeguru.repositories import categories as category_repo


class CategoryDialog(QDialog):
    """Add, rename, and remove the spending categories shown in the bill and
    expense pickers. Protected categories (Savings, Other) are listed but can't
    be renamed or deleted because the reporting layer depends on their names."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Categories")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        self._list = QListWidget()
        self._list.itemSelectionChanged.connect(self._on_selection_changed)
        self._list.itemDoubleClicked.connect(self._on_rename)
        layout.addWidget(self._list)

        btn_bar = QHBoxLayout()
        self._btn_add = QPushButton("Add")
        self._btn_rename = QPushButton("Rename")
        self._btn_delete = QPushButton("Delete")
        for btn in (self._btn_rename, self._btn_delete):
            btn.setEnabled(False)
        btn_bar.addWidget(self._btn_add)
        btn_bar.addWidget(self._btn_rename)
        btn_bar.addWidget(self._btn_delete)
        btn_bar.addStretch()
        layout.addLayout(btn_bar)

        self._btn_add.clicked.connect(self._on_add)
        self._btn_rename.clicked.connect(self._on_rename)
        self._btn_delete.clicked.connect(self._on_delete)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self._refresh()

    def _refresh(self) -> None:
        self._list.clear()
        for category in category_repo.get_all():
            label = category.name
            if category.is_protected:
                label += "  (built-in)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, category)
            self._list.addItem(item)
        self._on_selection_changed()

    def _selected(self) -> Category | None:
        item = self._list.currentItem()
        if item is None or not self._list.selectedItems():
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_selection_changed(self) -> None:
        category = self._selected()
        editable = category is not None and not category.is_protected
        self._btn_rename.setEnabled(editable)
        self._btn_delete.setEnabled(editable)

    def _name_taken(self, name: str, *, exclude_id: int | None = None) -> bool:
        target = name.strip().casefold()
        return any(
            c.name.casefold() == target and c.id != exclude_id
            for c in category_repo.get_all()
        )

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(self, "Add Category", "Category name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        if self._name_taken(name):
            QMessageBox.warning(self, "Add Category",
                                f"A category named “{name}” already exists.")
            return
        category_repo.add(name)
        self._refresh()

    def _on_rename(self) -> None:
        category = self._selected()
        if category is None or category.is_protected:
            return
        name, ok = QInputDialog.getText(
            self, "Rename Category", "New name:", text=category.name
        )
        if not ok:
            return
        name = name.strip()
        if not name or name == category.name:
            return
        if self._name_taken(name, exclude_id=category.id):
            QMessageBox.warning(self, "Rename Category",
                                f"A category named “{name}” already exists.")
            return
        category_repo.rename(category.id, name)
        self._refresh()

    def _on_delete(self) -> None:
        category = self._selected()
        if category is None or category.is_protected:
            return
        answer = QMessageBox.question(
            self,
            "Delete Category",
            f"Delete the “{category.name}” category?\n\n"
            "Bills and expenses already tagged with it keep their value; it is "
            "only removed from the pickers.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            category_repo.delete(category.id)
            self._refresh()
