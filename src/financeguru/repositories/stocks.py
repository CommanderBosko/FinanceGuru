from decimal import Decimal

from financeguru.db import get_connection
from financeguru.models.stock import Stock
from financeguru.money import optional_decimal, to_decimal


def get_all() -> list[Stock]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM stocks ORDER BY ticker").fetchall()
    return [_row_to_stock(r) for r in rows]


def add(stock: Stock) -> int | None:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO stocks (ticker, shares, purchase_price, purchase_date, notes)"
            " VALUES (?, ?, ?, ?, ?)",
            (stock.ticker, stock.shares, stock.purchase_price, stock.purchase_date, stock.notes),
        )
        return cur.lastrowid


def update(stock: Stock) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE stocks SET ticker=?, shares=?, purchase_price=?, purchase_date=?, notes=?"
            " WHERE id=?",
            (stock.ticker, stock.shares, stock.purchase_price, stock.purchase_date, stock.notes, stock.id),
        )


def delete(stock_id: int) -> None:
    with get_connection() as conn:
        conn.execute("DELETE FROM stocks WHERE id=?", (stock_id,))


def set_last_prices(prices: dict[str, Decimal], fetched_date: str) -> None:
    """Persist the latest fetched market price on every position with that ticker.

    Called after a completed price refresh so net-worth snapshots can value the
    portfolio without a network call. Tickers not in ``prices`` keep whatever
    price (or None) they already carry.
    """
    with get_connection() as conn:
        conn.executemany(
            "UPDATE stocks SET last_price=?, last_price_date=? WHERE ticker=?",
            [(price, fetched_date, ticker) for ticker, price in prices.items()],
        )


def _row_to_stock(row) -> Stock:
    return Stock(
        id=row["id"],
        ticker=row["ticker"],
        shares=to_decimal(row["shares"]),
        purchase_price=to_decimal(row["purchase_price"]),
        purchase_date=row["purchase_date"],
        notes=row["notes"],
        last_price=optional_decimal(row["last_price"]),
        last_price_date=row["last_price_date"],
    )
