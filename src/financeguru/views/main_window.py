import sys
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
from financeguru.views.charts_view import ChartsView
from financeguru.views.currency_converter_view import CurrencyConverterView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.debt_snowball_view import DebtSnowballView
from financeguru.views.expenses_view import ExpensesView
from financeguru.views.goals_view import GoalsView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.salary_view import SalaryView
from financeguru.views.stock_tips_view import StockTipsView
from financeguru.views.stocks_view import StocksView

def _icon_fallback_path() -> Path:
    # PyInstaller sets sys._MEIPASS in BOTH onefile (temp extraction dir) and
    # onedir (dist folder) mode — checking it covers both without a separate
    # sys.frozen branch. Never set in dev/Nix/Flatpak runs, where the
    # source-tree-relative SVG lookup below is unchanged. PNG (not SVG) is
    # used when frozen since it needs no Qt SVG plugin to rasterize.
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass) / "financeguru.png"
    return Path(__file__).parents[3] / "share" / "icons" / "hicolor" / "scalable" / "apps" / "financeguru.svg"


_ICON_FALLBACK = _icon_fallback_path()


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
        self._tabs.addTab(ExpensesView(), "Expenses")
        self._tabs.addTab(self._salary, "Income")
        self._tabs.addTab(StocksView(), "Stocks")
        self._tabs.addTab(StockTipsView(), "Stock Tips")
        self._tabs.addTab(DebtSnowballView(), "Debt Snowball")
        self._tabs.addTab(GoalsView(), "Goals")
        self._tabs.addTab(ChartsView(), "Charts")
        self._tabs.addTab(CurrencyConverterView(), "Currency Converter")

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

    def closeEvent(self, event) -> None:
        # Child widgets in a QTabWidget never receive their own close event, so
        # stop any in-flight fetch threads here — before the window (and the
        # QThreads parented to its views) are torn down — to avoid "QThread
        # destroyed while still running" aborting the process on quit.
        for i in range(self._tabs.count()):
            widget = self._tabs.widget(i)
            if hasattr(widget, "stop_threads"):
                widget.stop_threads()
        super().closeEvent(event)
