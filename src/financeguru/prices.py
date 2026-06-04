from PySide6.QtCore import QThread, Signal


class PriceFetcher(QThread):
    prices_ready = Signal(dict)   # {ticker: float | None}
    fetch_error = Signal(str)

    def __init__(self, tickers: list[str], parent=None):
        super().__init__(parent)
        self._tickers = tickers

    def run(self) -> None:
        try:
            import yfinance as yf
            prices: dict[str, float | None] = {}
            for ticker in self._tickers:
                try:
                    prices[ticker] = yf.Ticker(ticker).fast_info.last_price
                except Exception:
                    prices[ticker] = None
            self.prices_ready.emit(prices)
        except Exception as exc:
            self.fetch_error.emit(str(exc))
