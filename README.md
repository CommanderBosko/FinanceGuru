# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments, monitors a stock portfolio with live prices, provides analyst-backed stock tips, calculates debt payoff strategies, visualizes an income budget with savings projections, and plans savings goals with automatic monthly bill creation. Database backup, restore, and CSV export are built into the File menu. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — eight tabs fully implemented (Dashboard, Bills, Payments, Stocks, Stock Tips, Debt Snowball, Income, Goals). All features are functional and persisted to SQLite. The app launches from the system app menu on NixOS with a custom icon.

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
- **File menu** — Backup Database (WAL-safe, date-stamped, `chmod 600`), Restore Database (validates source is a real SQLite file before overwriting, clears stale WAL sidecars, refreshes all tabs), Export to CSV (one file per table in a chosen directory), and Quit (Ctrl+Q).
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
├── prices.py                     # PriceFetcher / AnalystFetcher QThreads — background yfinance lookups with timeout
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

**2026-06-07 (Night) — File Menu: Backup, Restore, and Export to CSV**

- Added a `&File` menu to the main window with four actions: Backup Database, Restore Database, Export to CSV, and Quit (Ctrl+Q).
- `backup_database` uses the SQLite online backup API for a transactionally consistent copy that merges WAL pages; output is `chmod 600`.
- `restore_database` validates the source file is real SQLite before overwriting, then clears any stale `-wal`/`-shm`/`-journal` sidecars; triggers a full tab refresh afterward.
- `export_all_csv` enumerates all user tables from `sqlite_master` and writes one CSV per table to a chosen directory; returns the list of written paths.

**2026-06-07 (Evening) — Goals Budgeting Tab**

- Added a new **Goals** tab (eighth tab, after Debt Snowball). Enter a goal name, total price, and target month; the app computes the monthly savings contribution and auto-creates a recurring "Goal" bill so the commitment appears in Bills and Dashboard.
- The "Afford By" date picker shows month + year only and snaps to the last day of the chosen month.
- An **Amount Left** column tracks `price − sum(payments against the goal's bill)`, floored at $0 — decreases each time the Goal bill is marked paid.
- Editing a goal updates its linked bill. Deleting a goal (with a confirmation dialog) also deletes its linked bill.
- Added `payment_repo.total_paid_by_bill()` — a single grouped-sum query returning a `dict[int, Decimal]` used by the Goals tab for efficient Amount Left computation.

**2026-06-07 (PM) — Right-Click Menus, Payments Search, and UX Polish**

- Added a reusable `attach_row_menu` helper (`context_menu.py`) and wired right-click context menus into all six data tables. Each menu mirrors the tab's toolbar buttons and reuses the same handlers; right-clicking selects the row under the cursor first.
- Added a live **search bar** to the Payments tab toolbar (right-aligned). Case-insensitive substring search across bill name, amount, date, and notes; filters in real time on every keystroke.
- Renamed the **"Salary" tab label to "Income"** in `main_window.py` (module and class names are unchanged).
- Fixed the **app icon missing from installed NixOS packages**: `flake.nix` now installs the hicolor SVG into the store prefix so `QIcon.fromTheme` resolves correctly outside `nix develop`.

**2026-06-07 — Payments Edit Button and Current-Month Filter**

- Added an **Edit** button and double-click-to-edit to the Payments tab, mirroring the Bills tab pattern. `PaymentDialog` now accepts an existing payment to pre-fill all fields; `payment_repo.update()` persists the changes.
- Added a **"This month only"** checkbox (checked by default) that filters the Payments list to the current calendar month. Uncheck to see the full payment history.

**2026-06-07 — Currency Precision (Decimal) and Security Hardening**

- Replaced all `float` monetary values with `decimal.Decimal` across models, repositories, views, and the Snowball/Avalanche simulator — eliminates IEEE-754 rounding error in month-by-month debt simulations. A `sqlite3` adapter binds `Decimal` transparently to existing `REAL` columns; no schema migration required.
- Locked `finance.db` file permissions to `0600` and the data directory to `0700` (plaintext financial data no longer world-readable).
- Added `validators.py` with `normalize_ticker()` — user-supplied tickers are restricted to a safe charset before reaching yfinance or the DB.
- Added 15-second per-ticker timeout to all yfinance calls; Refresh buttons re-enable via the thread's `finished` signal; threads are shut down cleanly on window close.
- Pinned `PySide6 >=6.7,<7` and `yfinance >=1.3,<2` in `pyproject.toml`; added `*.db`/`*.sqlite*` to `.gitignore`.
- Added identifier validation to `db.py:_ensure_column` to guard against injection through future non-literal callers.

**2026-06-05 — Stock Tips, Debt Snowball, Salary, and Lump-Sum Payments**

- Added Stock Tips tab with analyst consensus data fetched from yfinance.
- Added Debt Snowball tab with pure-Python Snowball/Avalanche simulator, per-debt payment schedule table, and one-time lump-sum extra payment support.
- Added Salary tab with multi-frequency income entry, monthly bill subtraction, and savings-rate slider with annual projections.
- Added "specific days" pay frequency (e.g., 1st and 15th) with a calendar day-picker grid.

**2026-06-04 — Project inception and full initial build**

- Scaffolded the entire project from scratch: Nix flake, pyproject.toml, SQLite schema, dataclasses, repository layer, and tabbed UI.
- Implemented Bills, Payments, Stocks, and Dashboard tabs.
- Added live price fetching via yfinance QThread, XDG desktop entry, and custom SVG app icon.
- Fixed multiple Nix packaging issues and wired Qt plugin paths via `qt6.wrapQtAppsHook`.

## Roadmap

- **NixOS integration** — Wire `financeguru.url` input into `~/NixOS/flake.nix` and add to a host's `environment.systemPackages`.
- **Tests** — `tests/` directory exists but is empty; add repository and simulation unit tests.
- **Error handling** — User-visible feedback when yfinance price or analyst data fetch fails.
- **Reporting / charts** — Spending over time, net worth trend using the salary, debt, and bill data now available.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented.
- **Schema migration utility** — Lightweight helper beyond the current try/except column-add approach.

## License

Personal use. No license declared.
