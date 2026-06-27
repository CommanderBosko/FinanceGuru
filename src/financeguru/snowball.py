from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from financeguru.models.debt import Debt
from financeguru.money import ZERO, CENT, cents, to_decimal

_MAX_MONTHS = 600
_MONTHS_PER_YEAR = Decimal(12)
_PERCENT = Decimal(100)


@dataclass
class DebtResult:
    name: str
    original_balance: Decimal
    apr: Decimal
    minimum_payment: Decimal
    payoff_month: int
    interest_paid: Decimal


@dataclass
class ScheduleMonth:
    month: int
    payments: list[Decimal]   # amount paid this month, aligned with PayoffPlan.debt_order
    total: Decimal


@dataclass
class PayoffPlan:
    strategy: str
    debt_results: list[DebtResult]   # sorted by payoff order
    debt_order: list[str]            # debt names in payment-priority order (schedule columns)
    schedule: list[ScheduleMonth]    # per-month payment breakdown
    total_months: int
    total_interest: Decimal
    capped: bool                     # True if simulation hit the 600-month limit


def calculate(
    debts: list[Debt],
    extra: float | Decimal,
    lump_sums: list[tuple[int, float | Decimal]] | None = None,
) -> tuple[PayoffPlan, PayoffPlan]:
    snowball = _simulate("Snowball", sorted(debts, key=lambda d: d.balance), extra, lump_sums)
    avalanche = _simulate("Avalanche", sorted(debts, key=lambda d: -d.interest_rate), extra, lump_sums)
    return snowball, avalanche


def payoff_date(payoff_month: int) -> str:
    today = date.today()
    total = today.month - 1 + payoff_month
    year = today.year + total // 12
    month = total % 12 + 1
    return date(year, month, 1).strftime("%b %Y")


def _simulate(
    strategy: str,
    ordered: list[Debt],
    extra: float | Decimal,
    lump_sums: list[tuple[int, float | Decimal]] | None = None,
) -> PayoffPlan:
    if not ordered:
        return PayoffPlan(strategy=strategy, debt_results=[], debt_order=[],
                          schedule=[], total_months=0, total_interest=ZERO, capped=False)

    # One-time payments collapsed to {month: total injected that month}
    lump_by_month: dict[int, Decimal] = {}
    for m, raw in (lump_sums or []):
        amount = to_decimal(raw)
        if m >= 1 and amount > 0:
            lump_by_month[m] = lump_by_month.get(m, ZERO) + amount

    states = [
        {"debt": d, "balance": d.balance, "interest_paid": ZERO, "payoff_month": None}
        for d in ordered
    ]
    # A debt entered with a zero (sub-cent) balance is already paid off. Mark it
    # up front so it doesn't trip the in-loop payoff roll-up — which would fold a
    # minimum payment the user isn't actually making into the snowball, paying
    # other debts off faster than reality — and so its payoff_month is never left
    # unset (None) when the results are sorted below.
    for s in states:
        if s["balance"] < CENT:
            s["balance"] = ZERO
            s["payoff_month"] = 0
    rolling_extra = max(ZERO, to_decimal(extra))
    month = 0
    capped = False
    schedule: list[ScheduleMonth] = []

    while month < _MAX_MONTHS:
        month += 1
        paid = [ZERO] * len(states)

        # Accrue monthly interest on each active debt
        for s in states:
            if s["balance"] > 0:
                interest = s["balance"] * (s["debt"].interest_rate / _PERCENT / _MONTHS_PER_YEAR)
                s["balance"] += interest
                s["interest_paid"] += interest

        # Pay minimum on each active debt
        for i, s in enumerate(states):
            if s["balance"] > 0:
                pay = min(s["balance"], s["debt"].minimum_payment)
                s["balance"] = max(ZERO, s["balance"] - pay)
                paid[i] += pay

        # Roll extra (recurring snowball + any one-time lump this month) toward
        # the highest-priority unpaid debt
        remaining = rolling_extra + lump_by_month.get(month, ZERO)
        for i, s in enumerate(states):
            if s["balance"] <= 0 or remaining <= 0:
                continue
            pay = min(s["balance"], remaining)
            s["balance"] = max(ZERO, s["balance"] - pay)
            remaining -= pay
            paid[i] += pay

        # Mark paid-off debts and grow rolling extra
        for s in states:
            if s["balance"] < CENT and s["payoff_month"] is None:
                s["balance"] = ZERO
                s["payoff_month"] = month
                rolling_extra += s["debt"].minimum_payment

        schedule.append(ScheduleMonth(
            month=month,
            payments=[cents(p) for p in paid],
            total=cents(sum(paid, ZERO)),
        ))

        if all(s["balance"] == 0 for s in states):
            break
    else:
        capped = True
        for s in states:
            if s["payoff_month"] is None:
                s["payoff_month"] = _MAX_MONTHS

    results = sorted(
        [
            DebtResult(
                name=s["debt"].name,
                original_balance=s["debt"].balance,
                apr=s["debt"].interest_rate,
                minimum_payment=s["debt"].minimum_payment,
                payoff_month=s["payoff_month"],
                interest_paid=cents(s["interest_paid"]),
            )
            for s in states
        ],
        key=lambda r: r.payoff_month,
    )

    return PayoffPlan(
        strategy=strategy,
        debt_results=results,
        debt_order=[d.name for d in ordered],
        schedule=schedule,
        total_months=month,
        total_interest=cents(sum((r.interest_paid for r in results), ZERO)),
        capped=capped,
    )
