# Project Brief — FinanceGuru Reporting / Charts (v1)

_Scoped via /interview on 2026-06-16. Reviewed by an independent agent; findings folded in._

## Goal
Give Natalie (sole user) a visual answer to *"where does my money go?"* and *"is my
spending creeping up?"* V1 ships spending-over-time; net-worth trend is a later phase.

## Spending model
**Spending universe = all `payments` + all `expenses`.** One special rule: a payment
against a bill tagged `notes = 'Goal'` is force-categorized as **Savings**. (Goal
contributions are already payments — not a separate addend. The "Goal" bill is an
ordinary bill row distinguished only by `notes = 'Goal'`, not a hidden/flagged row.)

## Must-haves

### Expense layer
- New **Expenses tab** — one-off expenses (amount, date, category, note), Add/Edit/Delete,
  toolbar + `attach_row_menu`, matching existing tab conventions.
- **Category** = plain `category TEXT NOT NULL DEFAULT 'Other'` column on `bills` and
  `expenses`. Canonical list as a Python constant: Housing, Utilities, Food, Transport,
  Health, Entertainment, Savings, Other. **No** categories table, **no** management UI.
- Payments inherit category via `LEFT JOIN bills` at read time; `bill_id IS NULL` →
  "Other"; `notes = 'Goal'` → "Savings".
- **Migration:** add column/table to `init_db()` executescript **and** `_ensure_column(...)`
  for live DBs; add `expenses` to `_CORE_TABLES`. Existing bills default "Other",
  re-categorized via the bill dialog.
- Money follows existing pattern: `to_decimal` at repo boundary; chart sums done in
  `Decimal`, cast to `float` only at the QtCharts boundary.

### Charts tab (reads `payments + expenses`)
- **Over-time chart**, 12-month window, **toggle**: total-per-month ↔ stacked-by-category.
  **Savings excluded from the total**, but present in stacked/pie views.
- **Breakdown pie**: defaults to current month, selectable to any of last 12 months.
- Both on one screen, **QtCharts** — first verify `from PySide6.QtCharts import QChart`
  imports in `nix develop`; if not, add `pkgs.qt6.qtcharts` to `flake.nix`.

## Out of scope (v1)
Net-worth trend; stocks/assets in charts; category management UI; recurring non-bill
expenses; budgets/limits/alerts; chart export.

## Definition of done
- Expenses tab full CRUD, persists with category; bills carry category, re-categorizable;
  migration runs clean on a live DB.
- Two pure data functions — `monthly_spending(window=12)` and
  `category_breakdown(year, month)` — pass pytest, including: Goal→Savings rule,
  Savings-excluded-from-total, uncategorized→"Other", sparse-data (<12 mo) degrades
  gracefully.
- Charts tab renders both charts, toggle + month-picker work (manual verify — no
  offscreen-Qt harness).
- `python -m pytest` green; app launches; all 8 existing tabs still `refresh()` without error.

## Risks
- QtCharts packaging may need a flake override beyond just adding `qtcharts` — settle
  before committing to the chart wiring.
- Sparse history makes charts thin until data accumulates (expected).
