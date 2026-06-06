# Project State — Finance Guru

_Last updated: 2026-06-05_

## Current Project State

The app has grown significantly from its 2026-06-04 inception. It now has seven tabs — Dashboard, Bills, Payments, Stocks, Stock Tips, Debt Snowball, and Salary — all fully functional and backed by SQLite. The working tree is clean and all commits are pushed to `origin/main`.

**What works:**
- Full Bills CRUD with Mark Paid (creates a linked Payment record; cascade-delete on bill removal)
- Payment history log with Add and Delete
- Stock portfolio table with Add/Edit/Delete and live price refresh via yfinance QThread
- Dashboard showing monthly bill status (Paid / Overdue / Upcoming) with cost summary, auto-refreshing on tab focus
- Stock Tips tab: track personal tips (action, target price, confidence, notes) with analyst consensus and mean price targets fetched from yfinance; cached in `stock_tips` table
- Debt Snowball tab: track debts with balance, APR, and minimum payment; month-by-month simulator computes both Snowball and Avalanche payoff schedules; side-by-side comparison of total interest and time saved; per-debt monthly payment schedule table; one-time lump-sum extra payments (windfalls)
- Salary tab: enter paychecks at any frequency (weekly through annual, or specific calendar days), normalized to a monthly figure; subtracts monthly bills to show surplus; savings-rate slider with proportional save-vs-spend bar and monthly/annual projections; supports multiple income sources per user
- App icon in system app menu, window title bar, and taskbar
- Nix `buildPythonApplication` packaging with desktop entry and icon installed to prefix
- Idempotent column migrations for schema additions (e.g., `pay_days` column added without breaking existing DBs)

**What is in progress / stub state:**
- `tests/` directory exists but contains no tests

**What is broken:**
- Nothing known

## Current Goals

### Short-term (next 1-3 sessions)
1. Wire the package into the NixOS flake at `~/NixOS/flake.nix` — add `financeguru.url` as an input and add the package to a host's `environment.systemPackages`.
2. Write initial tests for the repository layer (`bills.py`, `payments.py`, `stocks.py`, `debts.py`, `incomes.py`, `stock_tips.py`).
3. Add error handling / user-visible feedback when yfinance price or analyst data fetch fails.

### Long-term
- Multi-user data partitioning (bosko vs. natty views/profiles)
- Lightweight schema migration utility for adding columns to existing DBs
- Evaluate reporting / charts view (spending over time, net worth trend)

## Recent Decisions

- **No ORM** — Direct `sqlite3` calls via a thin repository layer. Keeps the dependency list minimal and the query intent explicit.
- **QThread for price fetching** — Avoids blocking the UI during yfinance network calls; `PriceFetcher` in `prices.py` emits a signal when done.
- **`QIcon.fromTheme` + SVG fallback** — Works correctly both as a NixOS system package and in `nix develop` dev mode.
- **Single `executescript` schema + idempotent column migrations** — Core DDL in `db.py:init_db()`; new columns added with `ALTER TABLE ... ADD COLUMN` guarded by exception catch so existing DBs are not broken.
- **Pure-Python snowball simulator** — `snowball.py` is a standalone month-by-month simulation with no external dependencies; handles rolling extra payments, lump-sum windfalls, and both strategies in a single pass.
- **`budget.py` shared normalization layer** — Frequency-to-monthly conversion logic (weekly, biweekly, semimonthly, monthly, annual, specific-days) lives in one place and is consumed by both the Salary view and the income repository.
- **Specific-days pay frequency** — Stores selected days as a comma-separated string in `pay_days`; monthly income is per-paycheck amount times count of selected days (treats each calendar date as one paycheck occurrence per month).

## Known Issues / Tech Debt

- No tests exist yet (`tests/` is an empty stub).
- No formal schema migration strategy — new columns are added with try/except `ALTER TABLE`; dropping or renaming columns still requires manual intervention.
- Multi-user support is not implemented; both users share the same SQLite file at `~/.local/share/financeguru/finance.db`.
- Stock price and analyst data fetching depends on yfinance / Yahoo Finance availability; no user-visible error handling for rate-limiting or network failure.
- The Debt Snowball simulator assumes all debts start at the current balance with no partial-month handling.

## Next Steps

1. Add `financeguru` as a NixOS flake input in `~/NixOS/flake.nix` and install to a host.
2. Add repository-layer pytest tests using an in-memory SQLite database.
3. Add user-visible error feedback when yfinance fetch fails (network error, rate limit).
4. Consider a reporting/charts tab: spending over time, net worth trend using salary + debt + bill data.
