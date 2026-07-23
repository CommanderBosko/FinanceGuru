# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments and one-off expenses, monitors a stock portfolio with live prices, provides analyst-backed stock tips, calculates debt payoff strategies, visualizes an income budget with savings projections, plans savings goals with automatic monthly bill creation, and charts where the money goes month to month. Database backup, restore, and CSV export are built into the File menu. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — ten tabs fully implemented (Dashboard, Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals, Charts). All features are functional and persisted to SQLite. The Charts tab now includes a **net-worth trend chart** drawn from the daily snapshots the app has been recording since 2026-07-02, rendered gap-honestly (no interpolation across days the app didn't run). The app records that snapshot and takes an automatic rotating backup at every launch, and CI (`nix flake check` via GitHub Actions) runs the package build, the full test suite, and a real launch of the packaged binary on every push. The flake's outputs are generated for both `x86_64-linux` and `aarch64-linux`. The app is installed as a NixOS system package on the `gaming` and `natalie-laptop` hosts and launches from the system app menu with a custom icon — as of 2026-07-07 the NixOS package build itself sets up its Qt runtime environment correctly (`dontWrapQtApps` + an explicit `postFixup` wrap), fixing a startup crash that had been present in every packaged build. A 160-test pytest suite covers the repositories, models, the `db`/`snowball`/`budget`/`prices`/`reporting`/`categories`/`snapshots` modules, the dashboard's overdue-bill rules, offscreen smoke tests of every view, and behavioral tests of the Expenses filters. Four audit passes (two security 2026-06-07, full 2026-06-17, whole-codebase 2026-06-26) have been completed with all findings addressed.

## Features

- **Dashboard** — Bills actually due this month with Paid / Overdue / Upcoming status badges and a monthly cost summary. Monthly bills appear every month, yearly bills only in their due month, and one-time bills only in their exact month and year. Unpaid one-time and yearly bills from past months are carried over as "Overdue (Month)" rows until paid — they never silently vanish — and count toward the Total/Remaining summary. Auto-refreshes on tab focus.
- **Net-worth snapshots** — A daily snapshot (stock value, debt total, goal savings, net worth) is recorded automatically at launch and updated after a full price refresh; the Charts tab's Net Worth view draws this history. One row per day; past rows are immutable.
- **Automatic backups** — A rotating daily backup is written at every launch (before any schema migration runs, so a bad migration is always recoverable) to `~/.local/share/financeguru/backups/`, keeping the newest 14. Manual pre-restore safety copies are never pruned.
- **Bills** — Full CRUD for recurring bills (name, amount, due day, recurrence, category). Recurrence is schedule-aware: `monthly` bills recur every month, `yearly` bills carry a due month, and `one-time` bills carry a full due month + year (the dialog reveals the right pickers per recurrence). Mark Paid creates a linked payment record. Deleting a bill cascades to its payments.
- **Payments** — Full payment history log sorted newest-first. Payments optionally reference a bill. Add, Edit (button or double-click), and Delete supported. A "This month only" checkbox (on by default) filters the list to the current calendar month; uncheck to see the full history. A live search bar filters by bill name, amount, date, or notes.
- **Expenses** — Log one-off, non-recurring expenses (amount, date, category, notes) with full Add/Edit/Delete CRUD, double-click to edit, and a right-click context menu. A "This month only" checkbox (on by default) scopes the table to the current calendar month, and a live search bar filters by amount, date, category, or notes — the same filter pair as the Payments tab. Categories are **user-managed**: a "Manage Categories…" button opens a dialog to add, rename, and delete categories (seeded with Housing, Utilities, Groceries, Restaurants, Transport, Health, Entertainment, Pets, Savings, Other). Savings and Other are protected (the reporting layer depends on them) and can't be renamed or deleted.
- **Charts** — Two sub-tabs. *Spending* visualizes the trailing 12 months: a stacked bar chart breaks each month's spending into categories, and a pie chart shows a single month's breakdown (defaults to the current month, with a picker for any of the last 12). Spending = all payments + all expenses; goal contributions (payments against a goal-linked bill, identified by the goals foreign key) are counted as "Savings" and excluded from the monthly spending total. *Net Worth* draws the daily snapshot history as a date-axis line chart — contiguous runs of snapshots (≤7 days apart) connect into lines, every snapshot is dotted, and longer gaps render as visible breaks rather than interpolated lines. Auto-refreshes on tab focus.
- **Stocks** — Portfolio holdings with ticker, shares, purchase price, date, total cost basis, and live market price / market value / gain-loss fetched via yfinance. Green/red gain-loss colouring. Refresh Prices button triggers a background QThread fetch.
- **Stock Tips** — Track personal tips (ticker, action, target price, confidence, notes). Refresh Analyst Data fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- **Debt Snowball** — Track debts (balance, APR, minimum payment). A pure-Python month-by-month simulator computes both Snowball and Avalanche payoff strategies with rolling extra payments. Side-by-side summary shows total interest paid and time saved per strategy. A per-debt monthly payment schedule table shows exactly how each month's payment is allocated. One-time lump-sum extra payments (windfalls, bonuses, tax refunds) can be injected at a specific month and cascade across debts.
- **Income** — Enter income sources at any frequency (weekly, biweekly, semimonthly, monthly, annual, or specific calendar days). All amounts are normalized to a monthly figure. The Monthly Budget summary subtracts both monthly bills **and this month's logged expenses** to show the "Extra Spending Money" actually left over. A savings-rate slider splits that remainder into a proportional save-vs-spend bar with monthly and annual projections.
- **Goals** — Enter a savings goal (name, total price, target month). The app computes the required monthly contribution (`price / months_remaining`, rounded up to the cent) and auto-creates a recurring "Goal" bill so the commitment appears in the Bills and Dashboard tabs. Editing a goal updates its linked bill; deleting a goal (with confirmation) deletes its linked bill. An "Amount Left" column tracks how much of the goal price remains unfunded as payments accumulate. The "Afford By" date always snaps to the last day of the chosen month.
- **Right-click context menus** — The data tables (Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals) support right-click context menus mirroring their toolbar buttons. Right-clicking selects the row under the cursor first; selection-dependent actions are disabled when nothing is selected.
- **File menu** — Backup Database (WAL-safe SQLite online backup API, `chmod 600` before write, date-stamped default filename), Restore Database (validates source carries all FinanceGuru core tables, writes a timestamped `.bak` safety copy, clears stale WAL sidecars, runs schema migrations, refreshes all tabs), Export to CSV (table identifiers validated, all cells — headers included — sanitized against formula injection, each file created `0600` so it's never briefly world-readable), and Quit (Ctrl+Q).
- **App icon** — Custom green-dollar SVG icon in the system app menu, window title bar, and taskbar. Loaded via `QIcon.fromTheme` with SVG fallback for dev mode. Correctly installed into the Nix store prefix.
- **NixOS packaging** — `buildPythonApplication` target in `flake.nix`; installs desktop entry and icon into the system prefix. Packages, checks, and devShells are generated per-system (`x86_64-linux` and `aarch64-linux`), so an ARM host can consume the flake unchanged.
- **CI** — `nix flake check` builds the package, runs the full pytest suite headlessly in the Nix sandbox, and actually launches the packaged binary under a virtual display (`xvfb-run` + `xcb`) to confirm its Qt runtime environment works, not just that it builds; a GitHub Actions workflow runs it on every push and pull request.

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

# Run what CI runs (package build + sandboxed test suite)
nix flake check

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
├── main.py                       # Entry point — auto_backup(), init_db(), snapshot capture, QApplication, MainWindow
├── db.py                         # SQLite connection + schema (init_db); row_factory=sqlite3.Row; Decimal adapter
├── money.py                      # Decimal helpers (to_decimal, cents, ZERO, CENT) + sqlite3 adapter
├── validators.py                 # normalize_ticker() — restricts user tickers before yfinance/DB
├── prices.py                     # PriceFetcher / TipFetcher QThreads — background yfinance lookups via a capped curl_cffi session; per-ticker failure reporting
├── snowball.py                   # Pure-Python Debt Snowball/Avalanche month-by-month simulator (Decimal)
├── budget.py                     # Shared frequency-to-monthly normalization (all pay frequencies, Decimal)
├── reporting.py                  # Spending aggregation for Charts: monthly_spending() + category_breakdown() (Decimal)
├── categories.py                 # Category seed list + PROTECTED_CATEGORIES + GOAL_NOTE/SAVINGS_CATEGORY constants
├── models/
│   ├── bill.py                   # Bill dataclass (with category)
│   ├── payment.py                # Payment dataclass
│   ├── expense.py                # Expense dataclass (one-off spending with category)
│   ├── stock.py                  # Stock dataclass
│   ├── stock_tip.py              # StockTip dataclass
│   ├── debt.py                   # Debt dataclass
│   ├── income.py                 # Income dataclass (with pay_days for specific-days frequency)
│   ├── goal.py                   # Goal dataclass + months_remaining() + monthly_savings()
│   ├── category.py               # Category dataclass (name, position, is_protected)
│   └── snapshot.py               # Snapshot dataclass (daily net-worth record)
├── repositories/
│   ├── bills.py                  # DB access for bills
│   ├── payments.py               # DB access for payments (includes total_paid_by_bill())
│   ├── expenses.py               # DB access for one-off expenses
│   ├── stocks.py                 # DB access for stocks
│   ├── stock_tips.py             # DB access for stock tips + analyst data update
│   ├── debts.py                  # DB access for debts
│   ├── incomes.py                # DB access for incomes
│   ├── goals.py                  # DB access for goals
│   ├── categories.py             # DB access for user-managed categories (get_all/names/add/rename/delete)
│   └── snapshots.py              # Daily net-worth snapshot capture (launch + post-price-refresh upsert)
└── views/
    ├── main_window.py            # QMainWindow with QTabWidget + File menu; refreshes all tabs on focus/restore
    ├── context_menu.py           # Reusable attach_row_menu helper for right-click table menus
    ├── dashboard_view.py         # Monthly bill status summary
    ├── bill_dialog.py            # Add/Edit bill form
    ├── bills_view.py             # Bills tab — table + Add/Edit/Delete/Mark Paid
    ├── payment_dialog.py         # Log payment form
    ├── payments_view.py          # Payments tab — history + Add/Edit/Delete + month filter + search
    ├── expense_dialog.py         # Add/Edit one-off expense form
    ├── expenses_view.py          # Expenses tab — table + Add/Edit/Delete + Manage Categories
    ├── category_dialog.py        # Manage Categories dialog (add/rename/delete; protects Savings/Other)
    ├── charts_view.py            # Charts tab — Spending (stacked bars + pie) and Net Worth (trend line) sub-tabs (QtCharts)
    ├── _table.py                 # Shared table-cell builders (right/center) + the money() display formatter
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
.github/workflows/
└── ci.yml                        # GitHub Actions — runs `nix flake check` on push/PR
```

## Recent Changes

**2026-07-23 — Skill-Library Maintenance (Internal)**

- Internal only, no user-facing changes: shipped two new project-local Claude-skills (`codebase-improvement-sweep`, `mechanical-sweep-refactor`) and ran a `skill-audit` sweep across all 7 project-local skills, fixing a stale doc, adding missing argument docs, and extracting two scripts.
- The skills' own smoke tests did close one real gap: a test now covers the debt-snowball simulator's `capped=True` path (a debt whose minimum payment can never outpace its interest), and a mechanical sweep modernized `Optional[X]` type hints to `X | None` across all data models. Suite 159 → 160 tests, all green.

**2026-07-16 — Net-Worth Trend Chart, Expenses Filters, Multi-System Flake**

- **Net-worth trend chart shipped** — the Charts tab now has Spending / Net Worth sub-tabs; the new view draws the accrued daily snapshots on a date axis, breaking the line wherever adjacent snapshots are more than 7 days apart and dotting every point, so days the app never ran show as honest gaps rather than interpolation.
- **Expenses tab filters** — "This month only" checkbox and live search, matching the Payments tab.
- **Multi-system flake** — packages/checks/devShells are generated for `x86_64-linux` and `aarch64-linux` via a `forAllSystems` helper; derivations unchanged.
- **Consistent money formatting** — all amounts now route through a single `money()` formatter (`$1,234.56`); the Expenses tab had drifted to a separator-less format.
- Suite 151 → 159 tests, all green; `nix flake check` (build + tests + real packaged-app launch) passes; CI confirmed green on the GitHub runner.

**2026-07-07 (evening) — CI Regression Guard for Packaged-App Startup**

- **Added a `nix flake check` check that launches the packaged app for real** (`checks.qt-launch` in `flake.nix`), under `xvfb-run` with `QT_QPA_PLATFORM=xcb`, failing the check if the process doesn't stay running. The previous package check only proved the derivation *builds* — exactly why the startup bug below shipped silently. `xcb` (not `offscreen`) was chosen so the check also exercises the `libxcb-cursor` dlopen path.

**2026-07-07 — Packaged-App Startup Fix + Skill Maintenance**

- **Fixed the NixOS-installed package failing to launch** with "no Qt platform plugin could be initialized" — a different bug from the 2026-07-04 devShell fix below, and one that had been present in every packaged build. `wrapQtAppsHook`'s automatic wrap pass was silently dropping `QT_PLUGIN_PATH` from the final wrapper (clobbered by `buildPythonApplication`'s own Python wrap running after it), and `libxcb-cursor.so` was still missing from the closure. Fixed with `dontWrapQtApps = true` plus an explicit `postFixup` wrap so the Qt environment lands on the final binary.
- Internal: added a `qt-nix-wrapper-diagnose` project skill and cleaned up the skill library (no functional/user-facing changes).

_Earlier session entries (including 2026-07-04's devShell Qt fix, 2026-07-02's snapshots/backups/CI batch, 2026-06-26's audit #4, and 2026-06-22's user-managed categories) are recorded in [session-summary.md](session-summary.md), [session-summary-archive.md](session-summary-archive.md), and git history._

## Roadmap

- **Charts polish** — GUI eyeball of the Charts/Expenses tabs on a real display (the new net-worth trend's gap breaks and axis density, legend/colour/pie-label readability); decide whether the stacked over-time chart should also exclude Savings.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented, and the two machines hold two independent SQLite files (a sync-vs-partition decision to make deliberately first).
- **Schema migrations** — No framework, but `init_db()` is the established migration point and the `db-migration` skill documents the procedure (additive columns, guarded idempotent data fixups, idempotent seeding). Column drop/rename is still manual SQL.

## License

Personal use. No license declared.
