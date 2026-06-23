"""Canonical spending categories and the constants that drive categorization.

This list is the *seed* for the user-managed ``categories`` table: on startup
``db.init_db()`` inserts any of these names that are missing (see the seeding
loop there), so a fresh database starts with this set and users grow it from the
Manage Categories dialog. The bill/expense pickers and the charts read the live
list from ``repositories.categories``; the reporting aggregation imports the
special constants below. Editing this list only affects newly-seeded databases.
"""

# Order is the seeded display order; user-added categories append after these.
CATEGORIES = [
    "Housing",
    "Utilities",
    "Groceries",
    "Restaurants",
    "Transport",
    "Health",
    "Entertainment",
    "Pets",
    "Savings",
    "Other",
]

# Assigned to any bill/expense/payment that has no explicit category.
DEFAULT_CATEGORY = "Other"

# Goal contributions are ordinary payments against a bill tagged with this note
# (see goals_view). They are force-categorized as savings in the reports.
SAVINGS_CATEGORY = "Savings"
GOAL_NOTE = "Goal"

# Categories the reporting layer hard-codes (Savings is force-applied to goal
# contributions; Other is the fallback for uncategorized rows). They must always
# exist and keep their exact names, so the management UI cannot rename or delete
# them. Seeded with is_protected=1.
PROTECTED_CATEGORIES = {SAVINGS_CATEGORY, DEFAULT_CATEGORY}
