from decimal import Decimal

from financeguru.models.stock import Stock
from financeguru.repositories import stocks


def test_add_and_round_trip():
    new_id = stocks.add(Stock(ticker="AAPL", shares=Decimal("10"),
                              purchase_price=Decimal("150.25"),
                              purchase_date="2025-01-15", notes="long term"))
    assert new_id

    rows = stocks.get_all()
    assert len(rows) == 1
    s = rows[0]
    assert s.ticker == "AAPL"
    assert s.shares == Decimal("10")
    assert s.purchase_price == Decimal("150.25")
    assert isinstance(s.purchase_price, Decimal)
    assert s.notes == "long term"


def test_get_all_orders_by_ticker():
    stocks.add(Stock(ticker="TSLA", shares=Decimal("1"),
                     purchase_price=Decimal("200"), purchase_date="2025-01-01"))
    stocks.add(Stock(ticker="AMD", shares=Decimal("1"),
                     purchase_price=Decimal("100"), purchase_date="2025-01-01"))
    assert [s.ticker for s in stocks.get_all()] == ["AMD", "TSLA"]


def test_update_and_delete():
    sid = stocks.add(Stock(ticker="AAPL", shares=Decimal("10"),
                           purchase_price=Decimal("150.25"),
                           purchase_date="2025-01-15"))
    assert sid
    stocks.update(Stock(id=sid, ticker="AAPL", shares=Decimal("15"),
                        purchase_price=Decimal("151.00"),
                        purchase_date="2025-01-15", notes="added more"))
    s = stocks.get_all()[0]
    assert s.shares == Decimal("15")
    assert s.notes == "added more"

    stocks.delete(sid)
    assert stocks.get_all() == []
