from financeguru.db import get_connection
from financeguru.models.stock import Stock


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


def _row_to_stock(row) -> Stock:
    return Stock(
        id=row["id"],
        ticker=row["ticker"],
        shares=row["shares"],
        purchase_price=row["purchase_price"],
        purchase_date=row["purchase_date"],
        notes=row["notes"],
    )
