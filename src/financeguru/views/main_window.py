from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMainWindow, QTabWidget

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

    def _on_tab_changed(self, index: int) -> None:
        # Refresh views whose figures depend on data edited in other tabs.
        widget = self._tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
