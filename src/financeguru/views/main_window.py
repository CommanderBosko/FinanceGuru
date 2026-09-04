import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from financeguru import db
from financeguru.views import _month_filter
from financeguru.views.bills_view import BillsView
from financeguru.views.charts_view import ChartsView
from financeguru.views.currency_converter_view import CurrencyConverterView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.debt_snowball_view import DebtSnowballView
from financeguru.views.expenses_view import ExpensesView
from financeguru.views.goals_view import GoalsView
from financeguru.views.notes_view import NotesView
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
        # Every tab whose data the global month selector drives (below) needs
        # a direct reference (not just the QTabWidget's own indexing) so
        # MainWindow can call its select_month()/select_all()/month_keys().
        # Bills, Goals and Notes additionally need one so a note's link
        # indicator can switch tabs and drive the target view's month — see
        # _on_notes_navigate.
        self._bills = BillsView()
        self._goals = GoalsView()
        self._notes = NotesView()
        self._payments = PaymentsView()
        self._expenses = ExpensesView()
        self._charts = ChartsView()
        self._stock_tips = StockTipsView()
        self._tabs = QTabWidget()
        # Tabs are ordered alphabetically, with Dashboard pinned first.
        self._tabs.addTab(self._dashboard, "Dashboard")
        self._tabs.addTab(self._bills, "Bills")
        self._tabs.addTab(self._charts, "Charts")
        self._tabs.addTab(CurrencyConverterView(), "Currency Converter")
        self._tabs.addTab(DebtSnowballView(), "Debt Snowball")
        self._tabs.addTab(self._expenses, "Expenses")
        self._tabs.addTab(self._goals, "Goals")
        self._tabs.addTab(self._salary, "Income")
        self._tabs.addTab(self._notes, "Notes")
        self._tabs.addTab(self._payments, "Payments")
        self._tabs.addTab(self._stock_tips, "Stock Tips")
        self._tabs.addTab(StocksView(), "Stocks")

        self._notes.navigate_requested.connect(self._on_notes_navigate)

        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Global month selector — a toolbar row above the tabs, always
        # visible regardless of which tab is active. Replaces the per-tab
        # month pickers this class used to own indirectly (each affected
        # view previously kept its own); see _rebuild_month_list and
        # _broadcast_month for the wiring.
        self._month_picker = QComboBox()
        month_bar = QHBoxLayout()
        month_bar.addWidget(QLabel("Month:"))
        month_bar.addWidget(self._month_picker)
        month_bar.addStretch()

        central = QWidget()
        central_layout = QVBoxLayout(central)
        central_layout.addLayout(month_bar)
        central_layout.addWidget(self._tabs)
        self.setCentralWidget(central)

        self._month_picker.currentIndexChanged.connect(self._on_global_month_changed)
        self._rebuild_month_list()

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
        # A restore can bring back wildly different data (new interesting
        # months appearing or disappearing across any of the 7 contributing
        # tabs), so the global list needs re-deriving here too, not just on
        # tab switch.
        self._rebuild_month_list()

    def _on_notes_navigate(self, target: str, year: int, month: int) -> None:
        # A note's link indicator was clicked — jump to the linked Bill's or
        # Goal's own tab and month (select_month falls back to "All" on
        # either view if that exact month isn't one of its populated entries).
        # The tab switch is done with signals blocked so _on_tab_changed's own
        # refresh() doesn't fire — select_month below already refreshes with
        # the right month, and doing both would be two DB round-trips per click.
        view = self._bills if target == "bills" else self._goals
        self._tabs.blockSignals(True)
        self._tabs.setCurrentWidget(view)
        self._tabs.blockSignals(False)
        view.select_month(year, month)
        # Propagate the resolved month (or "All", if select_month fell back)
        # to the toolbar's own display AND every other month-aware tab —
        # otherwise a tab that isn't currently visible (Notes included) keeps
        # filtering on its old key even though the toolbar now shows
        # something else, and nothing ever notices: _rebuild_month_list's
        # change-detection compares the toolbar's own (already-synced) value
        # against itself on the next tab switch and sees no change to
        # broadcast. `skip=view` avoids redriving the just-navigated-to tab
        # a second time (it already refreshed exactly once, above).
        self._sync_global_display(view._current_key)
        self._broadcast_month(view._current_key, skip=view)

    def _on_tab_changed(self, index: int) -> None:
        # Refresh views whose figures depend on data edited in other tabs.
        widget = self._tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
        # Cheap: only re-broadcasts to every tab if the selection actually
        # needs to change (see _rebuild_month_list), so this doesn't turn
        # every tab switch into an eight-tab refresh storm.
        self._rebuild_month_list()

    # ── Global month selector ─────────────────────────────────────────────
    # One shared (year, month)-or-"All" value drives Bills, Payments,
    # Expenses, Income, Goals, Notes, Charts' pie chart, and Stock Tips —
    # see the Project Brief this was built from for the full rationale.
    #
    # Which of those a given attribute is (does it contribute months to the
    # union? does it accept "All"?) is derived from what the view itself
    # implements (month_keys() / select_all()) rather than hand-maintained
    # in a second and third list here — adding a ninth month-aware tab to
    # _MONTH_AWARE_ATTRS below is then the only place that can be forgotten,
    # instead of three.
    _MONTH_AWARE_ATTRS = (
        "_bills", "_payments", "_expenses", "_salary", "_goals",
        "_notes", "_charts", "_stock_tips",
    )
    # Bills/Goals have a pre-existing "fall back to All if this exact month
    # isn't one of my own populated entries" contract in their select_month
    # (needed so a Notes-tab link click is never left on a dead selection —
    # see their own docstrings). Left alone, that would let the global
    # broadcast below silently diverge the toolbar from what these two tabs
    # actually render (toolbar says a specific month, tab shows "All"), so
    # the global path opts out of that fallback via strict=True.
    _STRICT_ON_GLOBAL = ("_bills", "_goals")

    def _rebuild_month_list(self) -> None:
        """Recompute the global month list from every contributing tab.

        The union is cheap (a handful of small DB reads), so this runs on
        every tab switch and DB restore, not just at startup — but it only
        broadcasts the (possibly new) selection to every consumer tab if the
        selection actually changed, so a routine rebuild that leaves the
        current month/"All" selection intact doesn't force all eight
        consumer tabs to refresh for nothing.
        """
        previous_key = self._month_picker.currentData() if self._month_picker.count() else None
        keys: set[tuple[int, int]] = set()
        for attr in self._MONTH_AWARE_ATTRS:
            view = getattr(self, attr)
            if hasattr(view, "month_keys"):
                keys.update(view.month_keys())
        _month_filter.populate_from_keys(self._month_picker, keys)
        new_key = self._month_picker.currentData()
        if new_key != previous_key:
            self._broadcast_month(new_key)

    def _broadcast_month(self, key: tuple[int, int] | None, skip=None) -> None:
        """Push the global month/"All" selection to every tab it drives.

        A view with no select_all() (Notes, Charts' pie chart) can't render
        "All" as content, so a global "All" is simply never forwarded to it
        — it keeps showing whichever specific month it was last on. Pass
        `skip` (a view instance) to omit one tab that the caller has already
        driven to this exact key itself, so it isn't refreshed twice.
        """
        for attr in self._MONTH_AWARE_ATTRS:
            view = getattr(self, attr)
            if view is skip:
                continue
            if key is None:
                if hasattr(view, "select_all"):
                    view.select_all()
                continue
            year, month = key
            if attr in self._STRICT_ON_GLOBAL:
                view.select_month(year, month, strict=True)
            else:
                view.select_month(year, month)

    def _sync_global_display(self, key: tuple[int, int] | None) -> None:
        """Reflect `key` in the global picker's own display, silently.

        Used after a Notes link-click already drove exactly one view's own
        select_month (see _on_notes_navigate) — rebroadcasting here would
        refresh every other consumer tab for no reason.
        """
        combo = self._month_picker
        index = 0
        for i in range(combo.count()):
            if combo.itemData(i) == key:
                index = i
                break
        combo.blockSignals(True)
        combo.setCurrentIndex(index)
        combo.blockSignals(False)

    def _on_global_month_changed(self, index: int) -> None:
        self._broadcast_month(self._month_picker.currentData())

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
