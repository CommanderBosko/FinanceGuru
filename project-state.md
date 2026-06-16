# Project State — Finance Guru

_Last updated: 2026-06-16 — added the expense-tracking layer + spending Charts tab (now 10 tabs)_

## Current Project State

The app has ten fully-functional tabs — Dashboard, Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals, and Charts — all backed by SQLite and packaged as a Nix flake. Two comprehensive security audits have been conducted and all actionable findings addressed. The File menu (Backup/Restore/Export CSV) received earlier security hardening: CSV injection protection, restore validation with pre-restore backup, identifier hardening in SQL/filenames, and file permission locking. The price-fetch path no longer leaks network details to the UI. The newest work added an arbitrary-expense tracking layer (one-off expenses with categories) plus a reporting/Charts tab that visualizes spending over the trailing 12 months.

**What works:**
- **File menu** — Backup Database (WAL-safe SQLite online backup API, `chmod 600` before data written, date-stamped default filename), Restore Database (validates source carries all FinanceGuru core tables before overwriting, writes timestamped `.bak` safety copy, clears stale WAL/SHM sidecars, calls `init_db()` to migrate older schema, refreshes all tabs, `chmod 600`), Export to CSV (table identifiers validated via `_IDENT_RE`, each cell sanitized with `_csv_safe()` to block formula injection, each output file `chmod 600`), Quit (Ctrl+Q)
- Full Bills CRUD with Mark Paid (creates a linked Payment record; cascade-delete on bill removal)
- Payment history log with Add, Edit (button and double-click), and Delete; "This month only" checkbox filters to the current YYYY-MM- prefix by default; unchecking shows full history; live search bar filters by bill name, amount, date, or notes
- Right-click context menus on all seven data tables (Bills, Payments, Income, Stocks, Stock Tips, Debt Snowball, Goals) — mirrors each tab's toolbar actions via the reusable `attach_row_menu` helper in `context_menu.py`; right-clicking selects the row under the cursor first
- Stock portfolio table with Add/Edit/Delete and live price refresh via yfinance QThread (per-request socket timeout capped at 8s through an injected curl_cffi session; button re-enables on completion)
- Dashboard showing monthly bill status (Paid / Overdue / Upcoming) with cost summary, auto-refreshing on tab focus
- Stock Tips tab: track personal tips with analyst consensus and mean price targets fetched from yfinance; cached in `stock_tips` table
- Debt Snowball tab: track debts with balance, APR, and minimum payment; month-by-month simulator computes both Snowball and Avalanche payoff schedules in exact `Decimal` arithmetic; side-by-side comparison; per-debt monthly payment schedule table; one-time lump-sum extra payments (windfalls)
- Income tab: enter paychecks at any frequency (weekly through annual, or specific calendar days), normalized to a monthly figure using exact `Decimal` division; subtracts monthly bills to show surplus; savings-rate slider with proportional save-vs-spend bar and monthly/annual projections
- Goals tab: add/edit/delete savings goals (name, price, Afford By month); monthly savings computed as `ceil(price / months_remaining)` with months floored at 1; each goal auto-creates and syncs a recurring "Goal" bill; Amount Left column = `price − sum(payments against the goal's bill)`, floored at $0; deleting a goal also deletes its linked bill (with confirm)
- Expenses tab: add/edit/delete one-off arbitrary expenses (amount, date, category, notes) with toolbar + double-click + right-click context menu; mirrors the Bills tab CRUD pattern; exposes a public `refresh()` so it updates on tab focus / after restore
- Charts tab (reporting): two QtCharts views on one screen — a stacked-by-category bar chart of spending over the trailing 12 months, and a per-month breakdown pie defaulting to the current month with a picker for any of the last 12. Reads unified spending (all payments + all expenses) via `reporting.py`. Auto-refreshes on tab focus
- Categories: a fixed canonical list (Housing, Utilities, Food, Transport, Health, Entertainment, Savings, Other) in `categories.py`; every bill and expense carries a `category` (defaults to "Other"). No category-management UI (v1)
- Spending model: a payment against a `notes='Goal'` bill is force-categorized "Savings"; Savings is shown in the breakdown/stacked views but **excluded** from the monthly spending total (saving isn't spending). All aggregation is done in `Decimal`, cast to `float` only at the QtCharts boundary
- App icon in system app menu, window title bar, and taskbar — correctly installed into the Nix store prefix
- Nix `buildPythonApplication` packaging with desktop entry and icon installed to prefix
- All monetary values represented as `Decimal` throughout models, repositories, views, and simulation — no IEEE-754 float error
- `sqlite3` adapter registered so `Decimal` binds transparently to `REAL` columns; existing databases load unchanged
- DB file permissions locked to `0600`, data directory to `0700`
- Ticker input validated and normalized via `normalize_ticker()` before reaching yfinance or the DB
- yfinance price values and analyst price targets sanity-checked (must be finite and positive) before display; NaN/inf/non-positive analyst targets are silently coerced to `None`
- Price and analyst fetch errors are logged to `stderr` as full tracebacks; only a generic user-facing message is emitted to the UI (no URLs, hostnames, or proxy details leaked)
- Dependency versions pinned in `pyproject.toml` (`PySide6 >=6.7,<7`, `yfinance >=1.3,<2`)
- `.gitignore` excludes `*.db` and `*.sqlite*`
- Two comprehensive security audits completed (2026-06-07); all actionable findings addressed
- Pytest suite (91 tests) run against a per-test temp-file SQLite database created via the real `init_db()` (`tests/conftest.py` fixture):
  - **`reporting.py`** (`test_reporting.py`) — payment inherits its bill's category, Goal-tagged payment → Savings, no-bill payment → Other, expense uses its own category, breakdown sums payments+expenses, month-boundary filtering, empty month → `{}`, float-at-boundary; `monthly_spending` window size + oldest-first ordering, Savings-excluded-from-total, sparse-history zero-fill
  - **`expenses.py`** (`test_expenses.py`) — CRUD round-trip, `Decimal`↔`REAL` exactness, default category "Other", `spent_date DESC` ordering
  - `bills`/`db` tests extended for the new `category` column (round-trip, default, `init_db()` creates it, `_ensure_column` legacy-DB migration) and the `expenses` core table (CSV export)
  - **Repositories + `Goal` model** — CRUD round-trips, `Decimal`↔`REAL` exactness, FK `ON DELETE CASCADE`/`SET NULL`, payment aggregation/month filtering, NULL preservation, `months_remaining`/`monthly_savings` math
  - **`db.py`** (`test_db.py`) — backup round-trip + `chmod 600`, restore reverts live data / writes the `.pre-restore-*.bak` safety copy / rejects a non-FinanceGuru SQLite file, `export_all_csv` (one file per table + headers + perms), `_csv_safe` formula-injection neutralization, `_ensure_column` idempotency + identifier rejection
  - **`snowball.py`** (`test_snowball.py`) — two-plan return, zero-interest payoff, snowball-by-balance vs avalanche-by-rate ordering, extra/lump-sum acceleration, interest accrual, empty input, `payoff_date` format
  - **`budget.py`** (`test_budget.py`) — every pay frequency, specific-days, unknown-frequency fallback, `parse_pay_days`/`format_pay_days`, `monthly_bill` across recurrence + inactive
  - **`prices.py`** (`test_prices.py`) — `_call_with_timeout` success / success-with-None / exception / timeout
- yfinance fetch surfaces **per-ticker** failures: `_safe_call` returns `(ok, value)` so a genuine empty result (e.g. delisted ticker → `ok=True, value=None`) is distinct from a fetch error (`ok=False`); `TipFetcher._fetch_one` additionally returns `(failed, data)` so a network error on one analyst field flags the ticker while genuinely-absent coverage does not; `PriceFetcher`/`TipFetcher` collect failed tickers and emit a `partial_error` signal; both stock views show a warning naming exactly which tickers could not be fetched
- **No leaked threads in `prices.py`** — the old `_call_with_timeout` daemon-thread wrapper (which could leave an orphaned thread running past its join while yfinance's own request finished) is gone. `_make_session()` returns a `curl_cffi` session that keeps yfinance's Chrome impersonation but subclasses `request()` to cap every request's socket timeout at 8s; both fetchers pass `session=` into `yf.Ticker(...)`. The native socket timeout — not a wrapper thread — now bounds every call

**What is in progress / stub state:**
- (none)

**What is broken:**
- Nothing known

## Current Goals

### Short-term (next 1-3 sessions)
1. **Net-worth trend** — the deferred half of the charts roadmap. Build a net-worth-over-time view from salary/debt/stock/goals data (the original "is my net worth going up?" question). Was explicitly out of scope for the Charts v1.
2. **Charts polish** — only validated headless so far; do a real GUI eyeball (legend readability, stacked-bar colours, pie label crowding with many categories). Consider whether the stacked over-time chart should also exclude Savings (currently the stacked/pie views include it, only the headline *total* excludes it).
3. (Optional) Add an offscreen-Qt test harness so the PySide6 views can be smoke-tested (Charts/Expenses still rely on manual visual verification).
4. Re-evaluate whether any *custom* retry / rate-limit handling is still worth adding — yfinance 1.3.0 already provides retry/backoff (`YfConfig.network.retries`) and `YFRateLimitError` on HTTP 429, so the original goal is largely redundant.

_Done this session: expense-tracking layer + spending Charts tab (10 tabs total); 91 tests; brief saved at `docs/charts-tab-brief.md`._

### Long-term
- Net-worth trend view (deferred charts phase — see short-term #1)
- Multi-user data partitioning (bosko vs. natty views/profiles)
- Lightweight schema migration utility for adding/renaming/dropping columns
- Category-management UI (add/edit/delete categories) — fixed list only in v1

## Recent Decisions

- **Spending universe = all payments + all expenses (not "+ goal contributions")** — goal contributions are already payments against an ordinary bill tagged `notes='Goal'` (not a hidden row), so adding them as a third addend would double-count. `reporting.py` categorizes a Goal-tagged payment as "Savings" via a single rule.
- **Savings excluded from the monthly total, included in the breakdown** — saving money isn't spending it, so a fat goal-contribution month shouldn't read as a big spending month. `monthly_spending` returns `total` (Savings out) and `by_category` (Savings in) from the same query; the views never recompute. (User decision during /interview.)
- **Charts over-time chart is always stacked-by-category** — the original Total↔By-category toggle was removed at the user's request mid-session; by-category is the more useful view for spotting unnecessary spending, so it's the only mode.
- **Category as a plain `TEXT` column, not a categories table** — fixed list + no management UI means a `category TEXT NOT NULL DEFAULT 'Other'` column on `bills`/`expenses` and a Python constant (`categories.py`) is sufficient; no FK, no lookup table. `GOAL_NOTE`/`SAVINGS_CATEGORY` live there too as the single source of truth (`goals_view` imports `GOAL_NOTE` from it).
- **`reporting.py` is a standalone aggregation module** — it cross-cuts payments+expenses+bills, so it lives outside any single repository and outside `budget.py` (which is income/bill normalization). Opens its own `get_connection()` like the repos; sums in `Decimal`, casts to `float` only at the return boundary where QtCharts consumes it.
- **`expenses` added to `_CORE_TABLES`** — keeps backup/restore validation consistent (restore re-runs `init_db()` anyway). Consequence: pre-feature backups are now rejected by restore validation — accepted for a sole-user pre-release app (user decision).
- **QtCharts needs no flake change** — verified `from PySide6.QtCharts import QChart` imports inside `nix develop`; it ships with the nixpkgs `pyside6` build. (Fallback documented in `docs/charts-tab-brief.md` if a future rebuild breaks it: add `pkgs.qt6.qtcharts`.)
- **New views expose a public `refresh()`** — `main_window` refreshes tabs by duck-typing `refresh()` on focus/after-restore; `PaymentsView` only has `_refresh` and is the cautionary example. `ExpensesView`/`ChartsView` both expose public `refresh()`.

- **Eliminate the thread layer rather than bound it (prices.py)** — the leak premise predated yfinance's curl_cffi move; yfinance 1.3.0 already applies a native per-request socket timeout, so the `_call_with_timeout` daemon-thread wrapper was redundant *and* the leak source. Removed it entirely in favor of a direct `_safe_call(fn) -> (ok, value)`; a stalled fetch now raises (surfaced as `ok=False`) instead of needing a wrapper thread to bound it.
- **Keep curl_cffi; subclass it instead of injecting a plain `requests.Session`** — the roadmap note ("inject a `requests.Session`") predated yfinance 1.3.0, which defaults to `curl_cffi.requests.Session(impersonate="chrome")`. The Chrome impersonation is what keeps Yahoo from blocking requests, so a plain session would have made fetches *less* reliable. `_make_session()` subclasses the curl_cffi session and keeps impersonation.
- **Cap the timeout inside `request()`, not via a session default** — yfinance passes `timeout=30` explicitly on every request, which overrides any session-level default. Clamping inside the overridden `request()` (`min(timeout, 8s)`) is the only effective lever.
- **`TipFetcher._fetch_one` returns `(failed, data)`** — with the daemon-thread join gone, a capped-timeout error now raises *inside* `_fetch_one` where the per-field `try/except` would otherwise swallow it. Returning an explicit `failed` flag lets a real network error mark the ticker failed while a ticker with genuinely no analyst coverage (no error, just empty data) is not flagged.
- **Tests use a per-test temp-file DB, not `:memory:`** — Each repository call opens a fresh `get_connection()`, and a `:memory:` SQLite database is private to a single connection, so it can't be shared across calls within one test. The autouse `temp_db` fixture in `tests/conftest.py` monkeypatches `db.DB_DIR`/`db.DB_PATH` to a `tmp_path` file and runs the real `init_db()`, exercising the actual schema, FK cascades, and the Decimal↔REAL round-trip.
- **Test helpers use typed keyword args, not `dict(**overrides)`** — A `dict(...).update(overrides)` builder widens every value to the union of all field types, which Pyright then rejects at the dataclass constructor. Plain typed-parameter factory functions keep the editor clean with no runtime change.
- **`_csv_safe()` uses apostrophe prefix** — OWASP-recommended approach; the apostrophe is stripped by spreadsheet apps before display so the user sees the original value while formula execution is blocked. Applied to every exported cell regardless of table.
- **Core-table validation in `restore_database`** — Checking for `_CORE_TABLES` (not merely that the file opens as SQLite) prevents any SQLite file from wiping the live database. Error message names missing tables to aid legitimate debugging.
- **Timestamped `.bak` before restore** — Keeps the current database recoverable immediately before overwrite; timestamp in the filename makes successive restores non-colliding.
- **`init_db()` after restore** — Migrates older-schema backups in place so the running code's expectations are always met. Idempotent — existing columns are unaffected.
- **Generic fetch-error message in `prices.py`** — Raw exceptions can contain URLs and hostnames; logging to stderr preserves debuggability without leaking environment details to the GUI.
- **`math.isfinite` + sign guard on analyst price target** — `yfinance` can return NaN when analyst coverage is sparse; filtering at parse boundary keeps `None` as the canonical sentinel and prevents `"nan"` in the UI.
- **SQLite online backup API for Backup** — Transactionally consistent even when a WAL sidecar is active; a raw `shutil.copy` would miss uncommitted WAL pages and produce a potentially inconsistent file.
- **Probe-before-overwrite replaced by core-table check** — The previous probe (`SELECT count(*) FROM sqlite_master`) confirmed the file was SQLite but allowed any SQLite file. The new check confirms the file is specifically a FinanceGuru database.
- **Sidecar cleanup on restore** — Removes `-wal`/`-shm`/`-journal` files after copying the restored database; without this SQLite would replay the old WAL on top of the restored data.
- **`_refresh_all()` uses duck-typing** — Calls `refresh()` on any tab widget that exposes it, requiring no registry and no changes when future tabs are added.
- **Backup filename defaults to `financeguru-backup-YYYYMMDD.db`** — A sensible default that avoids overwriting; the user can override freely in the Save dialog.
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

- Test coverage now spans the repositories, `Goal` model, `db.py` (backup/restore/CSV/`_csv_safe`), `snowball.py`, `budget.py`, and the `prices.py` timeout plumbing. The PySide6 **views** themselves remain untested (no offscreen-Qt harness yet).
- No formal schema migration strategy — new columns are added with try/except `ALTER TABLE`; dropping or renaming columns still requires manual intervention.
- Multi-user support is not implemented; both users share the same SQLite file at `~/.local/share/financeguru/finance.db`.
- Stock price and analyst data fetching depends on yfinance / Yahoo Finance availability. Whole-fetch and per-ticker failures are surfaced to the user (fetch details go to stderr). yfinance 1.3.0 provides retry/backoff and 429 handling itself; no custom layer added.
- **Residual security tech debt (intentionally deferred):**
  - `pyproject.toml` version ranges are fine under Nix (locked by `flake.lock`) but permissive enough to allow a breaking minor update for `pip install` users.
  - `yfinance` is an unofficial Yahoo Finance scraper — no SLA, no audit trail, can break on Yahoo API changes. Largest residual supply-chain exposure.
  - _(Resolved 2026-06-15 pm)_ The `prices.py` daemon-thread leak is fixed — the daemon-thread wrapper was removed and the per-request socket timeout is now capped via the injected curl_cffi session.
- The Debt Snowball simulator assumes all debts start at the current balance with no partial-month handling.

## Next Steps

1. Build the **net-worth trend** view (deferred charts phase) from salary/debt/stock/goals data.
2. GUI eyeball of the Charts/Expenses tabs (legend/colour/pie-label readability); decide whether the stacked over-time chart should also exclude Savings.
3. (Optional) Add an offscreen-Qt test harness so the views can be smoke-tested.
4. Re-evaluate whether any custom retry / rate-limit backoff is still worth adding given yfinance 1.3.0 already handles it.

_Done 2026-06-16: expense-tracking layer + spending Charts tab (commit `714adcd`); 91 tests; brief at `docs/charts-tab-brief.md`._
