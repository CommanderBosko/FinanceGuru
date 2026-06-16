"""Canonical spending categories and the constants that drive categorization.

A deliberately small, fixed list for v1 — no user-managed categories table and no
management UI. Both the bill/expense dialogs and the reporting aggregation import
from here so there is exactly one source of truth.
"""

# Order is the display order in the dialogs' combo boxes.
CATEGORIES = [
    "Housing",
    "Utilities",
    "Food",
    "Transport",
    "Health",
    "Entertainment",
    "Savings",
    "Other",
]

# Assigned to any bill/expense/payment that has no explicit category.
DEFAULT_CATEGORY = "Other"

# Goal contributions are ordinary payments against a bill tagged with this note
# (see goals_view). They are force-categorized as savings in the reports.
SAVINGS_CATEGORY = "Savings"
GOAL_NOTE = "Goal"
