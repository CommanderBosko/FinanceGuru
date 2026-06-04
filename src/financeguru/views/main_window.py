from PySide6.QtWidgets import QMainWindow, QTabWidget

from financeguru.views.bills_view import BillsView
from financeguru.views.dashboard_view import DashboardView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.stocks_view import StocksView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FinanceGuru")
        self.resize(1100, 720)

        self._dashboard = DashboardView()
        self._tabs = QTabWidget()
        self._tabs.addTab(self._dashboard, "Dashboard")
        self._tabs.addTab(BillsView(), "Bills")
        self._tabs.addTab(PaymentsView(), "Payments")
        self._tabs.addTab(StocksView(), "Stocks")

        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

    def _on_tab_changed(self, index: int) -> None:
        if index == 0:
            self._dashboard.refresh()
