# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments, monitors a stock portfolio with live prices, provides analyst-backed stock tips, calculates debt payoff strategies, visualizes an income budget with savings projections, and plans savings goals with automatic monthly bill creation. Database backup, restore, and CSV export are built into the File menu. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — eight tabs fully implemented (Dashboard, Bills, Payments, Stocks, Stock Tips, Debt Snowball, Income, Goals). All features are functional and persisted to SQLite. The app is installed as a NixOS system package on the `gaming` and `natalie-laptop` hosts and launches from the system app menu with a custom icon. A 69-test pytest suite covers the repositories, models, and the `db`/`snowball`/`budget`/`prices` modules.

## Features

- **Dashboard** — Bills due this month with Paid / Overdue / Upcoming status badges and a monthly cost summary. Auto-refreshes on tab focus.
- **Bills** — Full CRUD for recurring bills (name, amount, due day, frequency). Mark Paid creates a linked payment record. Deleting a bill cascades to its payments.
- **Payments** — Full payment history log sorted newest-first. Payments optionally reference a bill. Add, Edit (button or double-click), and Delete supported. A "This month only" checkbox (on by default) filters the list to the current calendar month; uncheck to see the full history. A live search bar filters by bill name, amount, date, or notes.
- **Stocks** — Portfolio holdings with ticker, shares, purchase price, date, total cost basis, and live market price / market value / gain-loss fetched via yfinance. Green/red gain-loss colouring. Refresh Prices button triggers a background QThread fetch.
- **Stock Tips** — Track personal tips (ticker, action, target price, confidence, notes). Refresh Analyst Data fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- **Debt Snowball** — Track debts (balance, APR, minimum payment). A pure-Python month-by-month simulator computes both Snowball and Avalanche payoff strategies with rolling extra payments. Side-by-side summary shows total interest paid and time saved per strategy. A per-debt monthly payment schedule table shows exactly how each month's payment is allocated. One-time lump-sum extra payments (windfalls, bonuses, tax refunds) can be injected at a specific month and cascade across debts.
- **Income** — Enter income sources at any frequency (weekly, biweekly, semimonthly, monthly, annual, or specific calendar days). All amounts are normalized to a monthly figure. Monthly bills are subtracted to show surplus spending money. A savings-rate slider splits the surplus into a proportional save-vs-spend bar with monthly and annual projections.
- **Goals** — Enter a savings goal (name, total price, target month). The app computes the required monthly contribution (`price / months_remaining`, rounded up to the cent) and auto-creates a recurring "Goal" bill so the commitment appears in the Bills and Dashboard tabs. Editing a goal updates its linked bill; deleting a goal (with confirmation) deletes its linked bill. An "Amount Left" column tracks how much of the goal price remains unfunded as payments accumulate. The "Afford By" date always snaps to the last day of the chosen month.
- **Right-click context menus** — All seven data tables (Bills, Payments, Income, Stocks, Stock Tips, Debt Snowball, Goals) support right-click context menus mirroring their toolbar buttons. Right-clicking selects the row under the cursor first; selection-dependent actions are disabled when nothing is selected.
- **File menu** — Backup Database (WAL-safe SQLite online backup API, `chmod 600` before write, date-stamped default filename), Restore Database (validates source carries all FinanceGuru core tables, writes a timestamped `.bak` safety copy, clears stale WAL sidecars, runs schema migrations, refreshes all tabs), Export to CSV (table identifiers validated, all cells sanitized against formula injection, each file `chmod 600`), and Quit (Ctrl+Q).
- **App icon** — Custom green-dollar SVG icon in the system app menu, window title bar, and taskbar. Loaded via `QIcon.fromTheme` with SVG fallback for dev mode. Correctly installed into the Nix store prefix.
- **NixOS packaging** — `buildPythonApplication` target in `flake.nix`; installs desktop entry and icon into the system prefix.

## Getting Started

### Prerequisites

- NixOS or any Linux system with Nix installed
- Nix flakes enabled (`experimental-features = nix-command flakes` in `nix.conf`)

### Installation (NixOS system package)

Add to your flake inputs:

```nix
financeguru.url = "github:CommanderBosko/FinanceGuru";
```

Then add to `environment.systemPackages`:

```nix
inputs.financeguru.packages.x86_64-linux.default
```

### Development

```bash
# Enter the dev environment (required before running anything)
nix develop

# Run the app
python -m financeguru.main

# Run tests
python -m pytest

# After adding a new flake dependency
nix flake update
```

### Configuration

The SQLite database is created automatically at first run:

```
~/.local/share/financeguru/finance.db
```

No manual configuration is required. New columns added between versions are applied automatically via idempotent `ALTER TABLE` migrations on startup.

## Project Structure

```
src/financeguru/
├── main.py                       # Entry point — init_db(), QApplication, MainWindow
├── db.py                         # SQLite connection + schema (init_db); row_factory=sqlite3.Row; Decimal adapter
├── money.py                      # Decimal helpers (to_decimal, cents, ZERO, CENT) + sqlite3 adapter
├── validators.py                 # normalize_ticker() — restricts user tickers before yfinance/DB
├── prices.py                     # PriceFetcher / TipFetcher QThreads — background yfinance lookups via a capped curl_cffi session; per-ticker failure reporting
├── snowball.py                   # Pure-Python Debt Snowball/Avalanche month-by-month simulator (Decimal)
├── budget.py                     # Shared frequency-to-monthly normalization (all pay frequencies, Decimal)
├── models/
│   ├── bill.py                   # Bill dataclass
│   ├── payment.py                # Payment dataclass
│   ├── stock.py                  # Stock dataclass
│   ├── stock_tip.py              # StockTip dataclass
│   ├── debt.py                   # Debt dataclass
│   ├── income.py                 # Income dataclass (with pay_days for specific-days frequency)
│   └── goal.py                   # Goal dataclass + months_remaining() + monthly_savings()
├── repositories/
│   ├── bills.py                  # DB access for bills
│   ├── payments.py               # DB access for payments (includes total_paid_by_bill())
│   ├── stocks.py                 # DB access for stocks
│   ├── stock_tips.py             # DB access for stock tips + analyst data update
│   ├── debts.py                  # DB access for debts
│   ├── incomes.py                # DB access for incomes
│   └── goals.py                  # DB access for goals
└── views/
    ├── main_window.py            # QMainWindow with QTabWidget + File menu; refreshes all tabs on focus/restore
    ├── context_menu.py           # Reusable attach_row_menu helper for right-click table menus
    ├── dashboard_view.py         # Monthly bill status summary
    ├── bill_dialog.py            # Add/Edit bill form
    ├── bills_view.py             # Bills tab — table + Add/Edit/Delete/Mark Paid
    ├── payment_dialog.py         # Log payment form
    ├── payments_view.py          # Payments tab — history + Add/Edit/Delete + month filter + search
    ├── stock_dialog.py           # Add/Edit stock holding form
    ├── stocks_view.py            # Stocks tab — holdings table + live prices
    ├── stock_tip_dialog.py       # Add/Edit stock tip form
    ├── stock_tips_view.py        # Stock Tips tab — tips table + analyst data refresh
    ├── debt_dialog.py            # Add/Edit debt form
    ├── debt_snowball_view.py     # Debt Snowball tab — CRUD + simulation + schedule + lump sums
    ├── income_dialog.py          # Add/Edit income form (all frequencies + day-picker for specific days)
    ├── salary_view.py            # Income tab — income list + budget visualizer + savings slider
    ├── goal_dialog.py            # Add/Edit goal form with live monthly-savings preview
    └── goals_view.py             # Goals tab — goal table + bill sync + Amount Left tracking
share/
├── applications/
│   └── financeguru.desktop       # XDG desktop entry for app menu
└── icons/hicolor/scalable/apps/
    └── financeguru.svg           # Custom green-dollar app icon
```

## Recent Changes

**2026-06-15 (pm) — Eliminated the prices.py Daemon-Thread Leak**

- Removed the `_call_with_timeout` daemon-thread wrapper that could leave an orphaned thread running past its join. Replaced with a direct `_safe_call(fn) -> (ok, value)`; yfinance 1.3.0's native socket timeout now bounds every call.
- Added `_make_session()`: a `curl_cffi` session that preserves yfinance's Chrome impersonation (so Yahoo doesn't block requests) but caps every request's socket timeout at 8s. Both fetchers pass `session=` into `yf.Ticker(...)`.
- `TipFetcher._fetch_one` now returns `(failed, data)` so a network error on one analyst field flags the ticker while genuinely-absent coverage does not.
- Suite 69 → 71 tests, all green.

**2026-06-15 — Test Coverage Beyond Repositories + Per-Ticker Fetch Feedback**

- Extended the pytest suite from 36 to 69 tests, adding coverage for `db.py` (backup/restore/export-CSV, `_csv_safe`, `_ensure_column`), `snowball.py` (payoff, Snowball/Avalanche ordering, extra & lump-sum payments, interest accrual), `budget.py` (every pay frequency + `monthly_bill` recurrence), and `prices.py` (`_call_with_timeout` plumbing).
- Surfaced **per-ticker** yfinance fetch failures: `_call_with_timeout` now returns `(ok, value)` so a genuine empty result is distinct from a timeout/error. `PriceFetcher`/`TipFetcher` collect failed tickers and emit a `partial_error` signal; both stock views warn naming exactly which tickers couldn't be fetched.
- Confirmed the package is already wired into `~/NixOS/flake.nix` and installed on the `gaming` and `natalie-laptop` hosts.

**2026-06-07 (Night #2) — Security Audit #2: CSV Injection, Restore Safety, File Perms**

Second comprehensive security audit of the ~3,500-line codebase, parallelized across three sub-agents (data layer, network/dependencies, file operations). All actionable findings addressed:

- **CRITICAL** — CSV/formula injection: `_csv_safe()` prefixes cells starting with `=`, `+`, `-`, `@`, TAB, or CR with an apostrophe, neutralizing spreadsheet formula execution when exported CSVs are opened in Excel or LibreOffice Calc.
- **MEDIUM** — Restore safety: `restore_database()` now rejects any file that lacks the FinanceGuru core tables (`bills`, `payments`, `stocks`, `incomes`, `debts`, `goals`, `stock_tips`), writes a timestamped `.pre-restore-YYYYMMDD-HHMMSS.bak` safety copy before overwriting, and calls `init_db()` post-restore so older-schema backups gain new columns.
- **MEDIUM** — Export identifier hardening: table names from `sqlite_master` are validated with `_IDENT_RE.fullmatch()` before SQL interpolation or filename use — blocks SQL injection and path traversal from a crafted database.
- **LOW** — Backup file permissions: `backup_database()` now `chmod 0o600`s the destination before writing; each exported CSV is also `chmod 0o600`.
- **LOW** — Price fetch error hygiene: `PriceFetcher` and `TipFetcher` log tracebacks to `stderr` and emit a generic message to the UI — no URLs, hostnames, or proxy details leaked. Analyst price targets are validated with `math.isfinite` and a sign guard before reaching the UI.

**2026-06-07 (Night) — File Menu: Backup, Restore, and Export to CSV**

- Added a `&File` menu to the main window with four actions: Backup Database, Restore Database, Export to CSV, and Quit (Ctrl+Q).
- `backup_database` uses the SQLite online backup API for a transactionally consistent copy that merges WAL pages; output is `chmod 600`.
- `restore_database` validates the source file is real SQLite before overwriting, then clears any stale `-wal`/`-shm`/`-journal` sidecars; triggers a full tab refresh afterward.
- `export_all_csv` enumerates all user tables from `sqlite_master` and writes one CSV per table to a chosen directory; returns the list of written paths.

_Earlier session entries are recorded in [session-summary-archive.md](session-summary-archive.md) and git history._

## Roadmap

- **Reporting / charts** — Spending over time, net worth trend using the salary, debt, bill, and goals data now available. (Top new-feature item.)
- **View tests** — Add an offscreen-Qt harness so the PySide6 views can be smoke-tested (the non-UI modules are covered).
- **yfinance robustness** — Native socket timeouts are now in place (daemon-thread leak resolved). yfinance 1.3.0 also provides retry/backoff and 429 handling itself, so any *custom* retry layer is likely redundant — re-evaluate before building.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented.
- **Schema migration utility** — Lightweight helper beyond the current try/except column-add approach.

## License

Personal use. No license declared.
