from decimal import Decimal

from financeguru.models.bill import Bill
from financeguru.models.payment import Payment
from financeguru.repositories import bills, payments


def _bill() -> int:
    bill_id = bills.add(Bill(name="Power", amount=Decimal("80.00"), due_day=15))
    assert bill_id
    return bill_id


def test_add_and_get_all_joins_bill_name():
    bill_id = _bill()
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-06-01",
                         bill_id=bill_id, notes="paid online"))

    rows = payments.get_all()
    assert len(rows) == 1
    rec = rows[0]
    assert rec["amount"] == Decimal("80.00")
    assert isinstance(rec["amount"], Decimal)
    assert rec["bill_name"] == "Power"
    assert rec["paid_date"] == "2026-06-01"


def test_get_all_orders_by_paid_date_desc():
    bill_id = _bill()
    payments.add(Payment(amount=Decimal("10"), paid_date="2026-01-01", bill_id=bill_id))
    payments.add(Payment(amount=Decimal("20"), paid_date="2026-03-01", bill_id=bill_id))
    payments.add(Payment(amount=Decimal("30"), paid_date="2026-02-01", bill_id=bill_id))
    dates = [r["paid_date"] for r in payments.get_all()]
    assert dates == ["2026-03-01", "2026-02-01", "2026-01-01"]


def test_update_and_delete():
    bill_id = _bill()
    pay_id = payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-06-01",
                                  bill_id=bill_id))
    assert pay_id
    payments.update(Payment(id=pay_id, amount=Decimal("82.50"),
                            paid_date="2026-06-02", bill_id=bill_id, notes="late fee"))
    rec = payments.get_all()[0]
    assert rec["amount"] == Decimal("82.50")
    assert rec["paid_date"] == "2026-06-02"
    assert rec["notes"] == "late fee"

    payments.delete(pay_id)
    assert payments.get_all() == []


def test_deleting_bill_cascades_to_payments():
    bill_id = _bill()
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-06-01", bill_id=bill_id))
    bills.delete(bill_id)
    assert payments.get_all() == []


def test_total_paid_by_bill_sums_per_bill():
    a = _bill()
    b = bills.add(Bill(name="Water", amount=Decimal("40.00"), due_day=10))
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-06-01", bill_id=a))
    payments.add(Payment(amount=Decimal("80.00"), paid_date="2026-07-01", bill_id=a))
    payments.add(Payment(amount=Decimal("40.00"), paid_date="2026-06-01", bill_id=b))
    # A payment with no bill is excluded from the per-bill totals.
    payments.add(Payment(amount=Decimal("5.00"), paid_date="2026-06-01", bill_id=None))

    totals = payments.total_paid_by_bill()
    assert totals == {a: Decimal("160.00"), b: Decimal("40.00")}


def test_get_paid_bill_ids_for_month_filters_by_prefix():
    a = _bill()
    b = bills.add(Bill(name="Water", amount=Decimal("40.00"), due_day=10))
    payments.add(Payment(amount=Decimal("80"), paid_date="2026-06-15", bill_id=a))
    payments.add(Payment(amount=Decimal("40"), paid_date="2026-07-15", bill_id=b))

    assert payments.get_paid_bill_ids_for_month(2026, 6) == {a}
    assert payments.get_paid_bill_ids_for_month(2026, 7) == {b}
    assert payments.get_paid_bill_ids_for_month(2026, 8) == set()
