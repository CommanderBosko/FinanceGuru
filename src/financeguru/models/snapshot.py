from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Snapshot:
    """One day's tracked net worth: stocks − debts + goal savings.

    "Tracked" because cash/bank balances aren't recorded anywhere in the app —
    this is the portion of net worth FinanceGuru can see, not the whole thing.
    """

    snap_date: str            # ISO yyyy-mm-dd; one snapshot per calendar day
    stock_value: Decimal      # Σ shares × (last_price, else purchase_price)
    debt_total: Decimal       # Σ debt balances
    goal_savings: Decimal     # Σ payments against goal-linked bills
    net_worth: Decimal        # stock_value − debt_total + goal_savings
    id: int | None = None
