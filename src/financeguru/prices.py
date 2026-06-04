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


# {ticker: {"action": str|None, "target": float|None, "count": int|None}}
TipData = dict[str, dict]


class TipFetcher(QThread):
    tips_ready = Signal(dict)
    fetch_error = Signal(str)

    def __init__(self, tickers: list[str], parent=None):
        super().__init__(parent)
        self._tickers = tickers

    def run(self) -> None:
        try:
            import yfinance as yf
            result: TipData = {}
            for ticker in self._tickers:
                result[ticker] = self._fetch_one(yf.Ticker(ticker))
            self.tips_ready.emit(result)
        except Exception as exc:
            self.fetch_error.emit(str(exc))

    @staticmethod
    def _fetch_one(t) -> dict:
        action = None
        target = None
        count = None
        try:
            pts = t.analyst_price_targets
            if pts and pts.get("mean"):
                target = float(pts["mean"])
        except Exception:
            pass
        try:
            summary = t.recommendations_summary
            if summary is not None and not summary.empty:
                # prefer current-month row, else most recent
                row = summary[summary["period"] == "0m"]
                if row.empty:
                    row = summary.iloc[[0]]
                row = row.iloc[0]
                strong_buy = int(row.get("strongBuy", 0))
                buy = int(row.get("buy", 0))
                hold = int(row.get("hold", 0))
                sell = int(row.get("sell", 0))
                strong_sell = int(row.get("strongSell", 0))
                count = strong_buy + buy + hold + sell + strong_sell
                scores = {
                    "Strong Buy": strong_buy * 2,
                    "Buy": buy * 1,
                    "Hold": hold * 0,
                    "Sell": sell * -1,
                    "Strong Sell": strong_sell * -2,
                }
                if count:
                    weighted = sum(scores.values()) / count
                    if weighted >= 1.0:
                        action = "Strong Buy"
                    elif weighted >= 0.4:
                        action = "Buy"
                    elif weighted >= -0.4:
                        action = "Hold"
                    elif weighted >= -1.0:
                        action = "Sell"
                    else:
                        action = "Strong Sell"
        except Exception:
            pass
        return {"action": action, "target": target, "count": count}
