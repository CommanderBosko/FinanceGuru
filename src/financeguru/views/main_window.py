from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QTabWidget,
)

from financeguru import db
from financeguru.views.bills_view import BillsView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.debt_snowball_view import DebtSnowballView
from financeguru.views.goals_view import GoalsView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.salary_view import SalaryView
from financeguru.views.stock_tips_view import StockTipsView
from financeguru.views.stocks_view import StocksView

_ICON_FALLBACK = Path(__file__).parents[3] / "share" / "icons" / "hicolor" / "scalable" / "apps" / "financeguru.svg"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Finance Guru")
        icon = QIcon.fromTheme("financeguru")
        if icon.isNull() and _ICON_FALLBACK.exists():
            icon = QIcon(str(_ICON_FALLBACK))
        if not icon.isNull():
            self.setWindowIcon(icon)
        self.resize(1100, 720)

        self._dashboard = DashboardView()
        self._salary = SalaryView()
        self._tabs = QTabWidget()
        self._tabs.addTab(self._dashboard, "Dashboard")
        self._tabs.addTab(BillsView(), "Bills")
        self._tabs.addTab(PaymentsView(), "Payments")
        self._tabs.addTab(self._salary, "Income")
        self._tabs.addTab(StocksView(), "Stocks")
        self._tabs.addTab(StockTipsView(), "Stock Tips")
        self._tabs.addTab(DebtSnowballView(), "Debt Snowball")
        self._tabs.addTab(GoalsView(), "Goals")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        self._build_menus()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        backup_action = QAction("&Backup Database…", self)
        backup_action.triggered.connect(self._backup_database)
        file_menu.addAction(backup_action)

        restore_action = QAction("&Restore Database…", self)
        restore_action.triggered.connect(self._restore_database)
        file_menu.addAction(restore_action)

        file_menu.addSeparator()

        export_action = QAction("&Export to CSV…", self)
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

    def _backup_database(self) -> None:
        default = str(Path.home() / f"financeguru-backup-{datetime.now():%Y%m%d}.db")
        path, _ = QFileDialog.getSaveFileName(
            self, "Backup Database", default, "SQLite database (*.db)"
        )
        if not path:
            return
        try:
            db.backup_database(Path(path))
        except Exception as exc:  # surface any I/O or sqlite error to the user
            QMessageBox.critical(self, "Backup Failed", str(exc))
            return
        QMessageBox.information(self, "Backup Complete", f"Database backed up to:\n{path}")

    def _restore_database(self) -> None:
        confirm = QMessageBox.warning(
            self,
            "Restore Database",
            "Restoring will overwrite your current data with the selected "
            "backup. This cannot be undone.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Restore Database", str(Path.home()), "SQLite database (*.db)"
        )
        if not path:
            return
        try:
            db.restore_database(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "Restore Failed", str(exc))
            return
        self._refresh_all()
        QMessageBox.information(self, "Restore Complete", "Database restored.")

    def _export_csv(self) -> None:
        dest = QFileDialog.getExistingDirectory(
            self, "Export to CSV — choose a folder", str(Path.home())
        )
        if not dest:
            return
        try:
            written = db.export_all_csv(Path(dest))
        except Exception as exc:
            QMessageBox.critical(self, "Export Failed", str(exc))
            return
        names = "\n".join(p.name for p in written)
        QMessageBox.information(
            self, "Export Complete", f"Exported {len(written)} file(s) to:\n{dest}\n\n{names}"
        )

    def _refresh_all(self) -> None:
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if hasattr(widget, "refresh"):
                widget.refresh()

    def _on_tab_changed(self, index: int) -> None:
        # Refresh views whose figures depend on data edited in other tabs.
        widget = self._tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
