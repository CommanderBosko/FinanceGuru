# Project State — Finance Guru

_Last updated: 2026-06-07 (Evening session)_

## Current Project State

The app has eight fully-functional tabs — Dashboard, Bills, Payments, Stocks, Stock Tips, Debt Snowball, Income, and Goals — all backed by SQLite and packaged as a Nix flake. The most recent session added the Goals tab: users enter a savings goal (name, price, target month) and the app computes the monthly savings contribution, auto-creates a linked recurring bill, and tracks Amount Left as payments accumulate.

**What works:**
- Full Bills CRUD with Mark Paid (creates a linked Payment record; cascade-delete on bill removal)
- Payment history log with Add, Edit (button and double-click), and Delete; "This month only" checkbox filters to the current YYYY-MM- prefix by default; unchecking shows full history; live search bar filters by bill name, amount, date, or notes
- Right-click context menus on all seven data tables (Bills, Payments, Income, Stocks, Stock Tips, Debt Snowball, Goals) — mirrors each tab's toolbar actions via the reusable `attach_row_menu` helper in `context_menu.py`; right-clicking selects the row under the cursor first
- Stock portfolio table with Add/Edit/Delete and live price refresh via yfinance QThread (with 15s per-ticker timeout and button re-enable on completion)
- Dashboard showing monthly bill status (Paid / Overdue / Upcoming) with cost summary, auto-refreshing on tab focus
- Stock Tips tab: track personal tips with analyst consensus and mean price targets fetched from yfinance; cached in `stock_tips` table
- Debt Snowball tab: track debts with balance, APR, and minimum payment; month-by-month simulator computes both Snowball and Avalanche payoff schedules in exact `Decimal` arithmetic; side-by-side comparison; per-debt monthly payment schedule table; one-time lump-sum extra payments (windfalls)
- Income tab: enter paychecks at any frequency (weekly through annual, or specific calendar days), normalized to a monthly figure using exact `Decimal` division; subtracts monthly bills to show surplus; savings-rate slider with proportional save-vs-spend bar and monthly/annual projections
- Goals tab: add/edit/delete savings goals (name, price, Afford By month); monthly savings computed as `ceil(price / months_remaining)` with months floored at 1; each goal auto-creates and syncs a recurring "Goal" bill; Amount Left column = `price − sum(payments against the goal's bill)`, floored at $0; deleting a goal also deletes its linked bill (with confirm)
- App icon in system app menu, window title bar, and taskbar — correctly installed into the Nix store prefix
- Nix `buildPythonApplication` packaging with desktop entry and icon installed to prefix
- All monetary values represented as `Decimal` throughout models, repositories, views, and simulation — no IEEE-754 float error
- `sqlite3` adapter registered so `Decimal` binds transparently to `REAL` columns; existing databases load unchanged
- DB file permissions locked to `0600`, data directory to `0700`
- Ticker input validated and normalized via `normalize_ticker()` before reaching yfinance or the DB
- yfinance price values sanity-checked (must be finite and positive) before display
- Dependency versions pinned in `pyproject.toml` (`PySide6 >=6.7,<7`, `yfinance >=1.3,<2`)
- `.gitignore` excludes `*.db` and `*.sqlite*`

**What is in progress / stub state:**
- `tests/` directory exists but contains no tests

**What is broken:**
- Nothing known

## Current Goals

### Short-term (next 1-3 sessions)
1. Wire the package into the NixOS flake at `~/NixOS/flake.nix` — add `financeguru.url` as an input and add the package to a host's `environment.systemPackages` (top priority).
2. Write initial tests for the repository layer (`bills.py`, `payments.py`, `stocks.py`, `debts.py`, `incomes.py`, `stock_tips.py`, `goals.py`) using an in-memory SQLite database; include `months_remaining` and `monthly_savings` unit tests for the `Goal` model.
3. Add user-visible error feedback when yfinance price or analyst data fetch fails.

### Long-term
- Multi-user data partitioning (bosko vs. natty views/profiles)
- Lightweight schema migration utility for adding/renaming/dropping columns
- Evaluate reporting/charts view (spending over time, net worth trend)

## Recent Decisions

- **Goal always snaps to last day of month** — The picker exposes only month + year; the stored `target_date` is always the final calendar day of that month. Ensures the goal is fully funded at month-end regardless of month length.
- **Linked bill tracks contributions** — Goal contributions are tracked as ordinary payments against a real "Goal" bill rather than a separate goals-payment table. Bills, Dashboard, and Income tabs automatically reflect the monthly commitment without special-casing.
- **`ON DELETE SET NULL` on `goals.bill_id`** — If the bill is deleted directly from the Bills tab, the goal row survives with `bill_id = NULL` and Amount Left gracefully shows the uncontributed full price.
- **Grouped-sum query in `total_paid_by_bill()`** — One SQL call (`SUM(amount) GROUP BY bill_id`) returns all bill contribution totals; `GoalsView._refresh()` does a dict lookup per goal, keeping refresh O(1) in DB round-trips.
- **`months_remaining` and `monthly_savings` live in the model** — Math is testable in isolation with no view or repository imports.
- **Reusable `attach_row_menu` helper** — A single `context_menu.py` module handles the `CustomContextMenu` setup for all seven data tables. Each caller passes a list of `(label, callback, needs_selection)` tuples; `None` entries become separators. Avoids duplicating 15–20 lines of boilerplate per view.
- **Search filter chains with month filter** — `_refresh()` applies the search string after the month filter, operating on the already-filtered row list. Keeps both filters independent and easy to reason about.
- **Match on displayed amount string** — Search checks the `Amount` column's display text (e.g., `"$42.00"`) rather than the raw `Decimal`, so users find rows by what they see.
- **Icon installed to Nix store** — `flake.nix` `postInstall` now copies the hicolor SVG alongside the `.desktop` file; `QIcon.fromTheme` can resolve it at runtime for installed packages (previously only worked in `nix develop`).
- **Client-side month filter in Payments** — `_refresh()` filters `get_all()` results in Python rather than adding a SQL `WHERE` clause; keeps the repository interface simple and the dataset is small enough that this is never a bottleneck.
- **`payment: dict` arg to `PaymentDialog`** — Pre-fill accepts the raw `sqlite3.Row`/dict from `_rows` directly, avoiding an extra conversion step and matching how the Bills dialog was structured.
- **Edit mirrors Bills tab button layout exactly** — Add, Edit, Delete left-aligned; stretch after; enabled/disabled by selection. Consistent UX across tabs.
- **`Decimal` stored as `REAL`** — Avoids a schema migration; cent-quantized values round-trip through SQLite `REAL` exactly within the 53-bit mantissa. The `sqlite3` adapter (registered in `money.py`) handles binding transparently.
- **Coerce at the read boundary** — Repositories convert `sqlite3.Row` values to `Decimal` once on load; all internal logic operates on exact types without defensive casting everywhere.
- **Backward-compatible FK cascade** — New databases get `ON DELETE CASCADE` on `payments.bill_id`; the explicit child-delete in `bills.delete()` is kept so databases created before this change still clean up correctly.
- **15-second per-ticker timeout via daemon thread** — Simplest portable approach since yfinance has no native timeout; daemon thread exits automatically on process termination if the join expires.
- **`normalize_ticker()` in `validators.py`** — Single validation point for user-supplied tickers; restricts to letters, digits, `.`, `-`, max 12 chars.
- **No ORM** — Direct `sqlite3` via a thin repository layer. Keeps dependencies minimal and queries explicit.
- **QThread for price fetching** — Avoids blocking the UI during yfinance network calls; `PriceFetcher`/`TipFetcher` in `prices.py` emit signals when done and are properly torn down on window close.
- **Pure-Python snowball simulator** — `snowball.py` is a standalone month-by-month simulation with no external dependencies; handles rolling extra payments, lump-sum windfalls, and both strategies in a single pass.
- **`budget.py` shared normalization layer** — Frequency-to-monthly conversion (all pay frequencies including specific-days) lives in one place.

## Known Issues / Tech Debt

- No tests exist yet (`tests/` is an empty stub).
- No formal schema migration strategy — new columns are added with try/except `ALTER TABLE`; dropping or renaming columns still requires manual intervention.
- Multi-user support is not implemented; both users share the same SQLite file at `~/.local/share/financeguru/finance.db`.
- Stock price and analyst data fetching depends on yfinance / Yahoo Finance availability; no user-visible error handling for rate-limiting or network failure.
- The Debt Snowball simulator assumes all debts start at the current balance with no partial-month handling.
- The app has not yet been wired into the NixOS system flake (`~/NixOS/flake.nix`).

## Next Steps

1. Add `financeguru` as a NixOS flake input in `~/NixOS/flake.nix` and install to a host.
2. Add repository-layer pytest tests using an in-memory SQLite database; include `models/goal.py` unit tests for `months_remaining` and `monthly_savings`.
3. Add user-visible error feedback when yfinance fetch fails (network error, rate limit).
4. Consider a reporting/charts tab: spending over time, net worth trend using salary + debt + bill + goals data.
