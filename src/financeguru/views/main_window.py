from PySide6.QtWidgets import QMainWindow, QTabWidget
from financeguru.views.bills_view import BillsView
from financeguru.views.payments_view import PaymentsView
from financeguru.views.stocks_view import StocksView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FinanceGuru")
        self.resize(1024, 700)

        tabs = QTabWidget()
        tabs.addTab(BillsView(), "Bills")
        tabs.addTab(PaymentsView(), "Payments")
        tabs.addTab(StocksView(), "Stocks")

        self.setCentralWidget(tabs)
