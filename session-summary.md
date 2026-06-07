# Session Summary — Finance Guru

---

## Session: 2026-06-07 (PM) — Right-Click Menus, Payments Search, and UX Polish

**Duration Estimate**: ~1 hour (17:16 – 17:43 based on commit timestamps)
**Session Focus**: Round out the app's UX by adding keyboard-alternative context menus to every data table and a live search bar to the Payments tab. Also renamed the Salary tab label to "Income" and fixed the icon missing from installed NixOS packages.

### What Was Accomplished

- Renamed the Salary tab display label from "Salary" to "Income" in `main_window.py`; the underlying `SalaryView` module and class name are unchanged.
- Fixed the app icon missing from installed NixOS packages: `flake.nix` `postInstall` previously only copied the `.desktop` file, so `QIcon.fromTheme("financeguru")` found no icon in the store for installed packages. The hicolor SVG is now installed to the prefix, making the icon work both in `nix develop` and on machines using the installed package.
- Created `src/financeguru/views/context_menu.py` — a reusable `attach_row_menu(table, actions)` helper. Right-clicking selects the row under the cursor first; actions with `needs_selection=True` are disabled when nothing is selected; `None` entries in the action list render as separators.
- Wired `attach_row_menu` into all six data tables: Bills, Payments, Income (SalaryView), Stocks, Stock Tips, and Debt Snowball. Each menu mirrors the tab's toolbar buttons and reuses the same handlers — no duplicate logic.
- Added a live search bar to the Payments toolbar (to the right of the existing controls, right-aligned via a stretch spacer). The filter is applied client-side in `_refresh()`: case-insensitive substring match across bill name, displayed amount string, date, and notes. The `QLineEdit.textChanged` signal re-runs `_refresh` on every keystroke. A clear button (`setClearButtonEnabled(True)`) lets the user reset the filter instantly.

### Files Changed

- `src/financeguru/views/main_window.py` — Tab label changed from `"Salary"` to `"Income"`
- `flake.nix` — `postInstall` extended to also install the hicolor SVG icon to the store output
- `src/financeguru/views/context_menu.py` — New module: `ActionSpec` type alias and `attach_row_menu` helper (new file)
- `src/financeguru/views/bills_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Mark Paid actions
- `src/financeguru/views/payments_view.py` — `attach_row_menu` wired in; search `QLineEdit` added to toolbar; `_refresh` updated to apply search filter after the month filter
- `src/financeguru/views/salary_view.py` — `attach_row_menu` wired in with Add/Edit/Delete actions
- `src/financeguru/views/stocks_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Refresh actions
- `src/financeguru/views/stock_tips_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Refresh Analyst Data actions
- `src/financeguru/views/debt_snowball_view.py` — `attach_row_menu` wired in with Add/Edit/Delete actions

### Commits This Session

- `db3e9c3` — feat(ui): rename Salary tab label to "Income"
- `7aa05cd` — fix(packaging): install app icon into store output
- `cbebb80` — feat(ui): add right-click context menus to all data tables
- `afe95d2` — feat(payments): add search bar filtering bills, amounts, dates, notes
- `108db6c` — style(payments): right-align the search bar in the toolbar

### Decisions Made

- **Reusable helper over per-view duplication** — `attach_row_menu` takes a generic `list[ActionSpec | None]`; every view passes its own callbacks. Adding menus to six tables required zero repeated logic.
- **Client-side search filter** — Applied in Python after `get_all()`, chained with the existing month filter. The payments dataset is small enough that this is never a bottleneck, and it avoids complicating the repository interface.
- **Match on displayed strings, not raw values** — The search checks the `Amount` column's display text (e.g., `"$42.00"`) rather than the raw `Decimal`, so users can search by what they see in the table.
- **`QLineEdit` right-aligned** — Stretch spacer before the search widget mirrors a standard browser/finder search bar placement and keeps the action buttons visually grouped on the left.

### Issues Encountered

- None. All changes are additive; no schema or model changes required.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-07 — Payments Edit Button and Current-Month Filter

**Duration Estimate**: Short follow-on session (same calendar day as previous session)
**Session Focus**: Round out the Payments tab to match the Bills tab's UX — add in-place editing of existing payment records and a quick toggle to filter the list down to the current month.

### What Was Accomplished

- Added `payment_repo.update()` — executes an `UPDATE payments SET ... WHERE id=?` using all mutable fields (`bill_id`, `amount`, `paid_date`, `notes`).
- Extended `PaymentDialog` to support editing an existing payment: accepts an optional `payment: dict` argument, switches the window title to "Edit Payment", stores the incoming `id` on `self._payment_id`, and pre-fills the bill combo, amount spinbox, date picker, and notes field via a new `_prefill()` method. The returned `Payment` dataclass now carries the original `id` so `payment_repo.update()` can target the correct row.
- Added an **Edit** button to the Payments toolbar (between Add and Delete), enabled/disabled in sync with the Delete button via `_on_selection_changed`. Clicking Edit opens a pre-filled `PaymentDialog`; accepting calls `payment_repo.update()` and refreshes the table.
- Wired **double-click-to-edit**: `QTableWidget.doubleClicked` connects to the same `_on_edit` handler so power users can bypass the button.
- Added a **"This month only"** `QCheckBox` to the right of the Delete button, checked by default. When checked, `_refresh()` filters `payment_repo.get_all()` to rows whose `paid_date` starts with the current `YYYY-MM-` prefix. Unchecking shows the full history. The checkbox state is wired via `toggled` → `_refresh`.

### Files Changed

- `src/financeguru/repositories/payments.py` — Added `update(payment: Payment) -> None`
- `src/financeguru/views/payment_dialog.py` — Optional `payment: dict` constructor arg; `_payment_id` field; `_prefill()` method; `id` included in returned `Payment`
- `src/financeguru/views/payments_view.py` — Added `Edit` button, `"This month only"` checkbox, `_on_edit()` handler, double-click-to-edit signal, updated `_on_selection_changed` to gate both buttons, client-side month filter in `_refresh()`

### Commits This Session

- _(staged, not yet committed — will be captured in the session-close commit)_

### Decisions Made

- **Client-side month filter** — The filter is applied in Python after `get_all()` rather than as a SQL `WHERE` clause, keeping the repository interface simple. The full dataset is small enough that this is never a bottleneck.
- **`payment: dict` rather than `Payment` dataclass** — `PaymentDialog` already received `sqlite3.Row` / dict-like objects from `_rows`; passing that directly avoids an extra conversion step and keeps the pre-fill code consistent with how the Bills dialog was already structured.
- **Edit button mirrors Bills tab pattern exactly** — Add, Edit, Delete left-aligned; stretch spacer after; enabled/disabled by selection. Consistency across tabs reduces cognitive overhead.

### Issues Encountered

- None. Changes are straightforward additions with no schema changes required.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-07 — Currency Precision (Decimal) and Security Hardening

**Duration Estimate**: ~30 minutes (09:42 – 10:11 based on commit timestamps)
**Session Focus**: Eliminate IEEE-754 float error from all monetary arithmetic and close out a full security audit covering DB permissions, input validation, dependency pinning, and network-call safety.

### What Was Accomplished

- Introduced `money.py` with helpers (`to_decimal`, `optional_decimal`, `cents`, `ZERO`, `CENT`) and registered a `sqlite3` adapter so `Decimal` values bind transparently to `REAL` columns — existing databases load unchanged.
- Migrated all currency, rate, and share fields in every model, repository, view, and simulation to `Decimal`. Float-to-Decimal coercion happens at the read boundary (repository layer); views convert back to `float` only for Qt spinboxes.
- Rewrote `snowball.py` to simulate entirely in `Decimal`, quantizing to cents only at the output boundary — eliminates error accumulation in up to 600-month simulations.
- Rewrote `budget.py` monthly normalization to use exact `Decimal` division from integer ratios instead of pre-rounded float factors.
- Locked down `finance.db` file permissions: data directory set to `0700`, database file set to `0600`, so plaintext financial data is not world-readable on multi-user machines.
- Added `prices.py` price validation: coerces `last_price` to a finite, positive value or `None` — prevents `nan`/`inf`/`None` from rendering as "nan" in market value and gain/loss columns.
- Added per-ticker 15-second timeout to every yfinance call (daemon thread + `join`) in both `PriceFetcher` and `TipFetcher`; re-enabled the Refresh button via the thread's `finished` signal; added `quit()`/`wait()` shutdown in `closeEvent`.
- Added `validators.py` with `normalize_ticker()` — restricts user-supplied tickers to letters, digits, `.`, `-` (max 12 chars) before they reach yfinance or the DB.
- Wired `normalize_ticker()` into `StockDialog` and `StockTipDialog` on both the Accept and Fetch paths.
- Added identifier validation to `db.py:_ensure_column` (table/column name allowlist + DDL prefix check) to close a latent injection sink.
- Added `ON DELETE CASCADE` to the `payments.bill_id` FK in the `init_db` schema for new databases; the repository-level explicit child delete is retained for backward compatibility with existing databases.
- Pinned `PySide6 (>=6.7,<7)` and `yfinance (>=1.3,<2)` in `pyproject.toml` so non-Nix pip installs cannot silently pull a regressed or malicious release.
- Added `*.db` / `*.sqlite*` patterns to `.gitignore` so the financial database can never be committed accidentally.

### Files Changed

- `src/financeguru/money.py` — New module: `Decimal` helpers and `sqlite3` adapter registration (new)
- `src/financeguru/db.py` — Decimal adapter; `0700`/`0600` fs permissions; `_ensure_column` identifier validation; FK cascade on `payments.bill_id`
- `src/financeguru/models/bill.py` — Currency fields changed to `Decimal`
- `src/financeguru/models/debt.py` — Balance, APR, and payment fields changed to `Decimal`
- `src/financeguru/models/income.py` — Amount field changed to `Decimal`
- `src/financeguru/models/payment.py` — Amount field changed to `Decimal`
- `src/financeguru/models/stock.py` — Price and share fields changed to `Decimal`
- `src/financeguru/models/stock_tip.py` — Price fields changed to `Decimal`
- `src/financeguru/repositories/bills.py` — Coerce money fields via `to_decimal` at read boundary; `ON DELETE CASCADE` note
- `src/financeguru/repositories/debts.py` — Coerce all numeric fields via `to_decimal`/`optional_decimal`
- `src/financeguru/repositories/incomes.py` — Coerce amount via `to_decimal`
- `src/financeguru/repositories/payments.py` — Coerce amount via `to_decimal`
- `src/financeguru/repositories/stock_tips.py` — Coerce price fields via `optional_decimal`
- `src/financeguru/repositories/stocks.py` — Coerce price/share fields via `to_decimal`/`optional_decimal`
- `src/financeguru/snowball.py` — Full simulation in `Decimal`; cent-quantize at output boundary
- `src/financeguru/budget.py` — Monthly normalization via exact `Decimal` division
- `src/financeguru/prices.py` — Price validation (finite, positive, or `None`); 15s per-ticker timeout in `PriceFetcher` and `TipFetcher`
- `src/financeguru/validators.py` — New `normalize_ticker()` function (new)
- `src/financeguru/views/bill_dialog.py` — Read `Decimal` via `float()` for spinboxes; build models with `cents()`
- `src/financeguru/views/dashboard_view.py` — Decimal-aware display
- `src/financeguru/views/debt_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/income_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/payment_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/stock_dialog.py` — Ticker normalized via `normalize_ticker()`; fetched price coerced to `Decimal`
- `src/financeguru/views/stock_tip_dialog.py` — Ticker normalized via `normalize_ticker()`
- `src/financeguru/views/stocks_view.py` — Re-enable Refresh button on `finished`; `quit()`/`wait()` on `closeEvent`
- `src/financeguru/views/stock_tips_view.py` — Re-enable Refresh button on `finished`; `quit()`/`wait()` on `closeEvent`
- `pyproject.toml` — Pinned `PySide6 >=6.7,<7` and `yfinance >=1.3,<2`
- `.gitignore` — Added `*.db` / `*.sqlite*`

### Commits This Session

- `dd62198` — fix(security): lock down DB perms, validate prices, bound fetch timeouts
- `c4a0cec` — harden(security): pin deps, validate tickers, guard DDL, FK cascade
- `38996f8` — refactor(money): represent currency as Decimal, not float

### Decisions Made

- **`Decimal` stored as `REAL`, not `TEXT`** — Avoids a schema migration; cent-quantized values round-trip through SQLite `REAL` exactly because they fit in the 53-bit mantissa. The `sqlite3` adapter handles binding transparently.
- **Coerce at the read boundary, not the write boundary** — Repositories convert incoming `sqlite3.Row` values to `Decimal` once; all internal logic then operates on exact types without defensive casting at every call site.
- **Backward-compatible FK cascade** — New databases get `ON DELETE CASCADE` on `payments.bill_id`; the explicit child-delete in `bills.delete()` is kept so existing databases (created before this change) still clean up correctly.
- **15-second per-ticker timeout via daemon thread** — The simplest portable approach for yfinance, which does not expose a native timeout parameter; the daemon thread exits automatically on process termination if the join timeout expires.

### Issues Encountered

- None blocking. All changes verified with Decimal unit tests, an offscreen GUI smoke test, and a live-DB load pass.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-05 — Stock Tips, Debt Snowball, Salary, and Lump-Sum Payments

**Duration Estimate**: ~4 hours (17:36 – 21:27 based on commit timestamps)
**Session Focus**: Expand the app from four tabs to seven by implementing Stock Tips, Debt Snowball with full payment simulation, and a Salary/budget visualizer — all fully wired into the existing SQLite schema.

### What Was Accomplished

- Implemented the Stock Tips tab: track personal tips (ticker, action, target price, confidence, notes) stored in a new `stock_tips` table; a Refresh Analyst Data button fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- Implemented the Debt Snowball tab: CRUD for debts (balance, APR, minimum payment); a pure-Python month-by-month simulator (`snowball.py`) computes both Snowball and Avalanche strategies with rolling extra payments; a side-by-side summary shows total interest paid and months saved per strategy.
- Added a detailed per-debt monthly payment schedule table to the Debt Snowball tab: shows exactly how much goes to minimum vs. rolling-extra payments for each debt each month; strategy-selectable.
- Added one-time lump-sum extra payments to the Debt Snowball calculator: model windfalls (tax refund, bonus) tied to a specific month; lump amount rolls onto the highest-priority debt first, cascading any leftover to the next debt; surfaced in both the summary and the schedule table.
- Implemented the Salary tab: income CRUD with paycheck frequency (weekly / biweekly / semimonthly / monthly / annual); normalizes all incomes to a monthly figure; subtracts monthly bills to show surplus spending money; a savings-rate slider splits surplus into a proportional save-vs-spend bar with monthly and annual projections.
- Added "specific days" pay frequency to the Salary tab: for paychecks tied to calendar dates (e.g., 1st and 15th); a day-picker grid (1–31) appears in the dialog; monthly income = per-paycheck amount × count of selected days; stored as comma-separated string in a new `pay_days` column with idempotent migration.
- All tabs now refresh on selection via `currentChanged` so cross-tab figures (bills total, income surplus) stay current.

### Files Changed

- `src/financeguru/db.py` — Added `stock_tips`, `debts`, and `incomes` table DDL; added `pay_days` column with try/except migration guard
- `src/financeguru/models/stock_tip.py` — `StockTip` dataclass (new)
- `src/financeguru/models/debt.py` — `Debt` dataclass (new)
- `src/financeguru/models/income.py` — `Income` dataclass with `pay_days` field
- `src/financeguru/repositories/stock_tips.py` — Full CRUD + analyst data update (new)
- `src/financeguru/repositories/debts.py` — Full CRUD for debts (new)
- `src/financeguru/repositories/incomes.py` — Full CRUD for incomes with `pay_days` support
- `src/financeguru/prices.py` — Extended with `AnalystFetcher` QThread for analyst consensus data
- `src/financeguru/snowball.py` — Pure-Python Snowball/Avalanche simulator with lump-sum support and monthly payment schedule recording (new)
- `src/financeguru/budget.py` — Shared frequency-to-monthly normalization, including specific-days logic
- `src/financeguru/views/main_window.py` — Wired Stock Tips, Debt Snowball, and Salary tabs; hooked `currentChanged` for all tab refresh
- `src/financeguru/views/stock_tip_dialog.py` — Add/Edit stock tip form (new)
- `src/financeguru/views/stock_tips_view.py` — Stock Tips tab view with Refresh Analyst Data (new)
- `src/financeguru/views/debt_dialog.py` — Add/Edit debt form (new)
- `src/financeguru/views/debt_snowball_view.py` — Debt Snowball tab with summary, schedule table, and lump-sum entry (new)
- `src/financeguru/views/income_dialog.py` — Add/Edit income form with specific-days day-picker grid
- `src/financeguru/views/salary_view.py` — Salary tab with budget visualizer and savings-rate slider

### Commits This Session

- `25f37bd` — feat: add Stock Tips tab with analyst data from yfinance
- `6b06eb8` — feat: add Debt Snowball tab with Snowball vs Avalanche comparison
- `1d661c1` — feat: add payment schedule table to Debt Snowball tab
- `16ef976` — feat: add one-time lump-sum payments to Debt Snowball calculator
- `401e9f7` — feat: add Salary tab with budget and savings visualizer
- `77f3027` — feat: add "specific days" pay frequency for exact paydays

### Decisions Made

- **Pure-Python snowball simulator** — No external dependencies; a single-pass month-by-month loop handles both strategies, rolling extra payments, and lump-sum windfalls. Keeps the logic testable and portable.
- **`budget.py` shared normalization layer** — Frequency-to-monthly math lives in one module consumed by the Salary view and income repository, avoiding duplication.
- **Specific-days stored as comma-separated string** — Simple to query and display; monthly income is amount × count of days, treating each calendar date as one paycheck per month.
- **Analyst data cached in DB** — yfinance data is written to `stock_tips` columns on refresh but never overwrites user-entered values; avoids repeated network calls on every view load.
- **Idempotent column migrations** — New columns added with `ALTER TABLE ... ADD COLUMN` inside a try/except so existing DBs silently receive the new column without requiring a manual migration step.

### Issues Encountered

- None blocking. The specific-days monthly calculation requires a deliberate modeling decision (count of selected days = paychecks per month); documented in project-state.md.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages`.
- Write pytest tests for the repository layer (bills, payments, stocks, debts, incomes, stock_tips) using an in-memory SQLite DB.
- Add user-visible error feedback when yfinance price or analyst data fetch fails.
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-04 — Project Inception and Full Initial Build

**Duration Estimate**: ~2.5 hours (08:14 – 10:35 based on commit timestamps)
**Session Focus**: Build the entire Finance Guru application from an empty repository to a fully functional, NixOS-packaged desktop app with four feature tabs.

### What Was Accomplished

- Scaffolded the full project: Nix flake (devShell + `buildPythonApplication`), `pyproject.toml`, SQLite schema, dataclass models, repository layer, and tabbed main window with stub views.
- Implemented the Bills tab with full CRUD (Add/Edit/Delete) and a Mark Paid action that creates a linked Payment record. Deleting a bill cascades to its payments.
- Implemented the Payments tab with a full history log sorted newest-first, plus Add and Delete.
- Implemented the Stocks tab with portfolio holdings (ticker, shares, purchase price, date, cost basis) and Add/Edit/Delete.
- Added live stock price fetching via yfinance; a `PriceFetcher` QThread updates Current Price, Market Value, and Gain/Loss columns with green/red colouring. Refresh Prices button triggers fetch.
- Added the Dashboard tab (first tab) showing all bills due this month with Paid/Overdue/Upcoming status badges and a total monthly cost summary. Refreshes automatically when the tab is focused via `currentChanged` signal.
- Fixed multiple Nix packaging issues: missing closing brace in `flake.nix`, added `qt6.qtbase` to `buildInputs`, switched build backend to `setuptools.build_meta`.
- Fixed `QT_QPA_PLATFORM` value quoting to prevent shell splitting on the semicolon separator.
- Suppressed the Adwaita icon theme warning in the devShell.
- Added `.gitignore` and removed committed `__pycache__` files.
- Added XDG desktop entry (`share/applications/financeguru.desktop`) so the app appears in the NixOS app menu; wired it into `flake.nix` installation.
- Created a custom green-dollar SVG icon (`share/icons/hicolor/scalable/apps/financeguru.svg`); fixed the `Icon=` key in the desktop entry to reference it.
- Set the window icon via `QIcon.fromTheme("financeguru")` with a SVG fallback path for dev mode — icon now appears in the title bar and taskbar.
- Corrected the window title from "FinanceGuru" to "Finance Guru".

### Files Changed

- `flake.nix` — Nix devShell and package definition; multiple fixes throughout the session (brace, buildInputs, build backend, QT_QPA_PLATFORM, Adwaita warning, desktop/icon install)
- `flake.lock` — Generated on first `nix flake update`
- `pyproject.toml` — Project metadata, dependencies (PySide6, yfinance), entry point
- `src/financeguru/db.py` — SQLite connection, `init_db()` schema (bills, payments, stocks tables)
- `src/financeguru/main.py` — Entry point; calls `init_db()` and launches `QApplication`/`MainWindow`
- `src/financeguru/prices.py` — `PriceFetcher` QThread for background yfinance price lookup
- `src/financeguru/models/bill.py` — `Bill` dataclass
- `src/financeguru/models/payment.py` — `Payment` dataclass
- `src/financeguru/models/stock.py` — `Stock` dataclass
- `src/financeguru/repositories/bills.py` — Bills CRUD repository
- `src/financeguru/repositories/payments.py` — Payments repository (get_all, add, delete, get_by_bill, get_payments_this_month)
- `src/financeguru/repositories/stocks.py` — Stocks CRUD repository
- `src/financeguru/views/main_window.py` — QMainWindow, tab setup, Dashboard refresh on tab switch, window title fix, window icon
- `src/financeguru/views/dashboard_view.py` — Monthly bill status table with cost summary
- `src/financeguru/views/bill_dialog.py` — Add/Edit bill form dialog
- `src/financeguru/views/bills_view.py` — Bills tab view
- `src/financeguru/views/payment_dialog.py` — Log payment form dialog
- `src/financeguru/views/payments_view.py` — Payments tab view
- `src/financeguru/views/stock_dialog.py` — Add/Edit stock holding dialog
- `src/financeguru/views/stocks_view.py` — Stocks tab view with live price columns
- `share/applications/financeguru.desktop` — XDG desktop entry
- `share/icons/hicolor/scalable/apps/financeguru.svg` — Custom app icon
- `.gitignore` — Excludes `__pycache__`, `.pyc`, `result`

### Commits This Session

- `58291ba` — Initial scaffold: PySide6 desktop app with SQLite backend
- `f73998b` — fix: quote QT_QPA_PLATFORM value to prevent shell splitting on semicolon
- `dacf0c2` — fix: suppress Adwaita icon theme warning in devShell
- `189db4e` — fix: add missing closing brace in flake.nix outputs attrset
- `12a2bec` — feat: implement Bills tab with full CRUD and Mark Paid
- `875d913` — chore: add .gitignore and remove cached pycache files
- `aeb4cc4` — feat: implement Payments tab with history, Add, and Delete
- `d590e92` — feat: implement Stocks tab with portfolio tracking
- `a6ee29b` — feat: live stock prices, Dashboard tab, and NixOS package build fixes
- `e92ccf0` — feat: add desktop entry so Finance Guru appears in the app menu
- `c0c6215` — feat: add custom app icon and fix desktop entry for proper launcher display
- `b08ee41` — fix: correct app title spacing to "Finance Guru"
- `d33962c` — feat: set window icon from app icon for title bar and taskbar

### Decisions Made

- **No ORM** — Direct `sqlite3` via a repository layer. Keeps the dependency surface minimal and queries explicit.
- **QThread for yfinance** — Background price fetching to avoid blocking the Qt event loop.
- **`QIcon.fromTheme` + SVG fallback** — Handles both installed (theme-registered) and dev-mode (source tree) execution contexts cleanly.
- **Single `executescript` schema** — All DDL in `db.py:init_db()`; trade-off is manual migration on schema changes.
- **`buildPythonApplication` packaging** — Enables `qt6.wrapQtAppsHook` to fix Qt plugin paths at install time; necessary for the app to run as a NixOS system package.

### Issues Encountered

- `flake.nix` had a missing closing brace that broke the Nix build; fixed in `189db4e`.
- `QT_QPA_PLATFORM=wayland;xcb` was being split by the shell on the semicolon; fixed with quoting in `f73998b`.
- `buildPythonApplication` initially lacked `qt6.qtbase` in `buildInputs` and used the wrong build backend; fixed in `a6ee29b`.
- The desktop entry's `Icon=` key referenced `utilities-finance` (a non-existent theme icon); replaced with the custom `financeguru` icon name in `c0c6215`.

### Remaining / Next Session

- Wire the package into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages`.
- Begin the Stock Tips tab (model, repository, dialog, view — fifth tab).
- Write pytest tests for the repository layer using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price fetch fails (network error, rate limit).

---
