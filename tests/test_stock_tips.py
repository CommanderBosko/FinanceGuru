from decimal import Decimal

from financeguru.models.stock_tip import StockTip
from financeguru.repositories import stock_tips


def _tip(id: int = 0, ticker: str = "NVDA", action: str = "Buy",
         target_price: Decimal | None = Decimal("1200.00"), confidence: int = 4,
         notes: str | None = "AI tailwind",
         added_date: str = "2026-06-01") -> StockTip:
    return StockTip(id=id, ticker=ticker, action=action,
                    target_price=target_price, confidence=confidence,
                    notes=notes, added_date=added_date)


def test_add_and_round_trip():
    new_id = stock_tips.add(_tip())
    assert new_id

    rows = stock_tips.get_all()
    assert len(rows) == 1
    t = rows[0]
    assert t.ticker == "NVDA"
    assert t.action == "Buy"
    assert t.target_price == Decimal("1200.00")
    assert isinstance(t.target_price, Decimal)
    assert t.confidence == 4
    # Analyst columns default to NULL until a fetch fills them.
    assert t.analyst_action is None
    assert t.analyst_target is None
    assert t.analyst_count is None


def test_null_target_price_preserved_as_none():
    stock_tips.add(_tip(ticker="WATCH", action="Watch", target_price=None))
    t = stock_tips.get_all()[0]
    assert t.target_price is None


def test_get_all_orders_by_ticker():
    stock_tips.add(_tip(ticker="ZM"))
    stock_tips.add(_tip(ticker="AMD"))
    assert [t.ticker for t in stock_tips.get_all()] == ["AMD", "ZM"]


def test_update_preserves_added_date_and_changes_fields():
    tid = stock_tips.add(_tip())
    stock_tips.update(_tip(id=tid, action="Hold", target_price=Decimal("1100.00"),
                           confidence=2, notes="cooling off"))
    t = stock_tips.get_all()[0]
    assert t.action == "Hold"
    assert t.target_price == Decimal("1100.00")
    assert t.confidence == 2
    assert t.added_date == "2026-06-01"


def test_update_analyst_data():
    tid = stock_tips.add(_tip())
    stock_tips.update_analyst_data(tid, action="Strong Buy", target=1300.0,
                                   count=42, updated="2026-06-10")
    t = stock_tips.get_all()[0]
    assert t.analyst_action == "Strong Buy"
    assert t.analyst_target == Decimal("1300.0")
    assert t.analyst_count == 42
    assert t.analyst_updated == "2026-06-10"


def test_delete():
    tid = stock_tips.add(_tip())
    stock_tips.delete(tid)
    assert stock_tips.get_all() == []
