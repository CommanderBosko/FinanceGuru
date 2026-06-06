# Session Summary — Finance Guru

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
