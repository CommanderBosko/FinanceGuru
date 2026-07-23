import re
from decimal import Decimal

from financeguru.models.debt import Debt
from financeguru.snowball import calculate, payoff_date


def _debt(name, balance, rate, minimum) -> Debt:
    return Debt(
        id=0,
        name=name,
        balance=Decimal(balance),
        interest_rate=Decimal(rate),
        minimum_payment=Decimal(minimum),
        notes=None,
    )


def test_calculate_returns_snowball_and_avalanche():
    debts = [_debt("A", "1000", "0", "100")]
    snowball, avalanche = calculate(debts, extra=0)
    assert snowball.strategy == "Snowball"
    assert avalanche.strategy == "Avalanche"


def test_single_zero_interest_debt_pays_off_cleanly():
    snowball, _ = calculate([_debt("A", "1000", "0", "100")], extra=0)
    assert snowball.total_months == 10
    assert snowball.total_interest == Decimal("0.00")
    assert snowball.debt_results[0].payoff_month == 10
    assert not snowball.capped


def test_snowball_orders_by_balance_avalanche_by_rate():
    debts = [
        _debt("Big", "5000", "5", "100"),
        _debt("Small", "1000", "20", "50"),
    ]
    snowball, avalanche = calculate(debts, extra=0)
    # Snowball attacks the smallest balance first.
    assert snowball.debt_order == ["Small", "Big"]
    # Avalanche attacks the highest interest rate first.
    assert avalanche.debt_order == ["Small", "Big"]  # Small also has the higher rate here


def test_avalanche_prioritizes_highest_rate_independent_of_balance():
    debts = [
        _debt("LowRateSmall", "1000", "3", "50"),
        _debt("HighRateBig", "5000", "25", "100"),
    ]
    _, avalanche = calculate(debts, extra=0)
    assert avalanche.debt_order == ["HighRateBig", "LowRateSmall"]


def test_extra_payment_speeds_up_payoff():
    debts = [_debt("A", "1000", "0", "100")]
    base, _ = calculate(debts, extra=0)
    boosted, _ = calculate(debts, extra=100)
    assert boosted.total_months < base.total_months


def test_lump_sum_speeds_up_payoff():
    debts = [_debt("A", "2000", "0", "100")]
    base, _ = calculate(debts, extra=0)
    with_lump, _ = calculate(debts, extra=0, lump_sums=[(2, 1000)])
    assert with_lump.total_months < base.total_months


def test_interest_accrues_on_a_positive_apr_debt():
    snowball, _ = calculate([_debt("Card", "1000", "24", "100")], extra=0)
    assert snowball.total_interest > Decimal("0")


def test_empty_debts_returns_zeroed_plan():
    snowball, avalanche = calculate([], extra=0)
    for plan in (snowball, avalanche):
        assert plan.total_months == 0
        assert plan.debt_results == []
        assert plan.total_interest == Decimal("0")
        assert not plan.capped


def test_payoff_date_formats_as_month_year():
    assert re.fullmatch(r"[A-Z][a-z]{2} \d{4}", payoff_date(3))


def test_debt_that_never_amortizes_is_capped():
    # Minimum payment (1) doesn't cover the monthly interest accrual on a
    # 50% APR balance, so the balance never shrinks and the simulation
    # should hit the 600-month cap instead of looping forever.
    snowball, _ = calculate([_debt("Spiral", "10000", "50", "1")], extra=0)
    assert snowball.capped
    assert snowball.total_months == 600
    assert snowball.debt_results[0].payoff_month == 600
