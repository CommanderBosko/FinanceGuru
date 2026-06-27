# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments and one-off expenses, monitors a stock portfolio with live prices, provides analyst-backed stock tips, calculates debt payoff strategies, visualizes an income budget with savings projections, plans savings goals with automatic monthly bill creation, and charts where the money goes month to month. Database backup, restore, and CSV export are built into the File menu. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — ten tabs fully implemented (Dashboard, Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals, Charts). All features are functional and persisted to SQLite. Spending categories are user-managed (a seeded `categories` table with an in-app Manage Categories dialog), and the Income tab's savings calculator nets out the current month's logged expenses. The app is installed as a NixOS system package on the `gaming` and `natalie-laptop` hosts and launches from the system app menu with a custom icon. A 113-test pytest suite covers the repositories, models, and the `db`/`snowball`/`budget`/`prices`/`reporting`/`categories` modules — including the price/tip fetcher QThreads and the category rename migration. Four audit passes (two security 2026-06-07, full 2026-06-17, whole-codebase 2026-06-26) have been completed with all findings addressed — the latest fixed a stale-data-after-restore bug across four tabs plus a batch of security/correctness/quality hardening.

## Features

- **Dashboard** — Bills actually due this month with Paid / Overdue / Upcoming status badges and a monthly cost summary. Monthly bills appear every month, yearly bills only in their due month, and one-time bills only in their exact month and year. Auto-refreshes on tab focus.
- **Bills** — Full CRUD for recurring bills (name, amount, due day, recurrence, category). Recurrence is schedule-aware: `monthly` bills recur every month, `yearly` bills carry a due month, and `one-time` bills carry a full due month + year (the dialog reveals the right pickers per recurrence). Mark Paid creates a linked payment record. Deleting a bill cascades to its payments.
- **Payments** — Full payment history log sorted newest-first. Payments optionally reference a bill. Add, Edit (button or double-click), and Delete supported. A "This month only" checkbox (on by default) filters the list to the current calendar month; uncheck to see the full history. A live search bar filters by bill name, amount, date, or notes.
- **Expenses** — Log one-off, non-recurring expenses (amount, date, category, notes) with full Add/Edit/Delete CRUD, double-click to edit, and a right-click context menu. Categories are **user-managed**: a "Manage Categories…" button opens a dialog to add, rename, and delete categories (seeded with Housing, Utilities, Groceries, Restaurants, Transport, Health, Entertainment, Pets, Savings, Other). Savings and Other are protected (the reporting layer depends on them) and can't be renamed or deleted.
- **Charts** — Visualizes spending over the trailing 12 months. A stacked bar chart breaks each month's spending into categories; a pie chart shows a single month's breakdown (defaults to the current month, with a picker for any of the last 12). Spending = all payments + all expenses; goal contributions (payments against a goal-linked bill, identified by the goals foreign key) are counted as "Savings" and excluded from the monthly spending total. Auto-refreshes on tab focus.
- **Stocks** — Portfolio holdings with ticker, shares, purchase price, date, total cost basis, and live market price / market value / gain-loss fetched via yfinance. Green/red gain-loss colouring. Refresh Prices button triggers a background QThread fetch.
- **Stock Tips** — Track personal tips (ticker, action, target price, confidence, notes). Refresh Analyst Data fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- **Debt Snowball** — Track debts (balance, APR, minimum payment). A pure-Python month-by-month simulator computes both Snowball and Avalanche payoff strategies with rolling extra payments. Side-by-side summary shows total interest paid and time saved per strategy. A per-debt monthly payment schedule table shows exactly how each month's payment is allocated. One-time lump-sum extra payments (windfalls, bonuses, tax refunds) can be injected at a specific month and cascade across debts.
- **Income** — Enter income sources at any frequency (weekly, biweekly, semimonthly, monthly, annual, or specific calendar days). All amounts are normalized to a monthly figure. The Monthly Budget summary subtracts both monthly bills **and this month's logged expenses** to show the "Extra Spending Money" actually left over. A savings-rate slider splits that remainder into a proportional save-vs-spend bar with monthly and annual projections.
- **Goals** — Enter a savings goal (name, total price, target month). The app computes the required monthly contribution (`price / months_remaining`, rounded up to the cent) and auto-creates a recurring "Goal" bill so the commitment appears in the Bills and Dashboard tabs. Editing a goal updates its linked bill; deleting a goal (with confirmation) deletes its linked bill. An "Amount Left" column tracks how much of the goal price remains unfunded as payments accumulate. The "Afford By" date always snaps to the last day of the chosen month.
- **Right-click context menus** — The data tables (Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals) support right-click context menus mirroring their toolbar buttons. Right-clicking selects the row under the cursor first; selection-dependent actions are disabled when nothing is selected.
- **File menu** — Backup Database (WAL-safe SQLite online backup API, `chmod 600` before write, date-stamped default filename), Restore Database (validates source carries all FinanceGuru core tables, writes a timestamped `.bak` safety copy, clears stale WAL sidecars, runs schema migrations, refreshes all tabs), Export to CSV (table identifiers validated, all cells — headers included — sanitized against formula injection, each file created `0600` so it's never briefly world-readable), and Quit (Ctrl+Q).
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
│   └── category.py               # Category dataclass (name, position, is_protected)
├── repositories/
│   ├── bills.py                  # DB access for bills
│   ├── payments.py               # DB access for payments (includes total_paid_by_bill())
│   ├── expenses.py               # DB access for one-off expenses
│   ├── stocks.py                 # DB access for stocks
│   ├── stock_tips.py             # DB access for stock tips + analyst data update
│   ├── debts.py                  # DB access for debts
│   ├── incomes.py                # DB access for incomes
│   ├── goals.py                  # DB access for goals
│   └── categories.py             # DB access for user-managed categories (get_all/names/add/rename/delete)
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
    ├── charts_view.py            # Charts tab — stacked monthly spending + category breakdown pie (QtCharts)
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

**2026-06-26 — Whole-Codebase Audit (#4) + Fixes**

- **Stale-data-after-restore bug fixed**: `Restore Database` reported success while the Payments, Stocks, Stock Tips, and Debt Snowball tabs kept showing pre-restore data — those four views only had private refresh methods, so the refresh-all gate skipped them. All views now expose a public `refresh()`.
- **Security/data hardening**: CSV exports are created `0600` up front (no world-readable window) with header cells also sanitized; `get_connection()` is now a context manager that closes the connection deterministically.
- **Correctness**: the Debt Snowball simulator no longer lets a zero-balance debt inflate the rolling payment pool; ticker validation rejects degenerate symbols (e.g. `A..B`, trailing separators); analyst-count cells are guarded against NaN; an unknown income frequency is logged rather than silently treated as monthly.
- **Quality**: right/center table-cell builders deduped into `views/_table.py`; chart axes are deleted on rebuild; the stock-tip dialog frees its previous fetcher; bill/debt dialogs validate a non-empty name; models default their category from `DEFAULT_CATEGORY`.
- Suite remains 113 tests, all green; fixes verified with headless offscreen-Qt smokes.

**2026-06-22 — User-Managed Categories, Category Rename Migration, Savings-Calc Expenses**

- **User-managed categories**: promoted spending categories from a fixed Python list to a seeded `categories` table with a `Category` model, a `categories` repository, and a "Manage Categories…" dialog (add/rename/delete) launched from the Expenses tab. Savings and Other are protected (the reporting layer hard-codes them). Bill/expense pickers and the charts read the live list, so additions appear without a restart. Category columns stay free text, so deleting a category only removes it from the pickers.
- **Renamed Food→Groceries and Eating out→Restaurants**: updated the seed list and added a guarded, idempotent `_rename_category` migration in `init_db()` that renames the row **and re-tags** existing bills/expenses, running before the seeding loop so the old name isn't re-added.
- **Savings calculator nets out the month's expenses**: the Income tab's Monthly Budget now subtracts `expenses.total_for_month(current)` on top of bills, with a new "This Month's Expenses" line.
- **Tooling**: two more project-local skills — `db-migration` (the safe `init_db()`-based schema-change procedure) and `new-feature` (the end-to-end layered build checklist).
- Suite 100 → 113 tests (category repo + rename-migration + `total_for_month`), all green.

**2026-06-17 — Audit Pass #3, Per-Month Bill Scheduling, Tooling Skills**

- **Audit + fixes**: hardened QThread teardown on exit (views nested in a `QTabWidget` never receive `closeEvent`, so the fetcher cleanup was dead code and could abort the app on quit mid-fetch). `MainWindow.closeEvent` now drives a `stop_threads()` hook, dialogs clean up in `done()`, and a cancellable `_TickerFetcher`/`stop_fetcher` cancels then waits (bounded, with an unbounded fallback). Scoped the dashboard to bills genuinely due this month, and made goal→Savings categorization key off the `goals.bill_id` foreign key instead of the `notes='Goal'` string (collision fix).
- **Per-month bill scheduling**: added nullable `due_month` (yearly) and `due_year` (one-time) columns plus `Bill.is_due_in()`, so yearly and one-time bills appear on the dashboard in their actual month instead of being dropped or counted every month.
- **Tooling**: two project-local skills under `.claude/skills/` — `qt-smoke` (headless offscreen-Qt verification of views/dialogs) and `audit` (comprehensive review orchestrating security + correctness + the project risk checklist + tests).
- Suite 91 → 100 tests (added fetcher QThread signal/cancel/stop coverage), all green.

**2026-06-16 — Expense Tracking Layer + Spending Charts Tab**

- Added two new tabs (8 → 10): **Expenses** (one-off expense CRUD with categories) and **Charts** (a stacked by-category bar chart of spending over the trailing 12 months plus a per-month breakdown pie, built on QtCharts).
- New data layer: `categories.py` (fixed category list, single source of truth for the `GOAL_NOTE`/`SAVINGS_CATEGORY` constants), a `category` column on `bills` (with migration) and a new `expenses` table, the `Expense` model + repository, and `reporting.py` with `monthly_spending(window=12)` and `category_breakdown(year, month)`.
- Spending is unified across **all payments + all expenses**; a payment against a "Goal" bill is categorized as Savings and excluded from the headline monthly total (saving isn't spending), but shown in the breakdown. All aggregation is done in `Decimal`, cast to `float` only at the chart boundary.
- Suite 69 → 91 tests, all green.

_Earlier session entries are recorded in [session-summary.md](session-summary.md), [session-summary-archive.md](session-summary-archive.md), and git history._

## Roadmap

- **Net-worth trend** — The deferred half of the charts work: a net-worth-over-time view from salary, debt, stock, and goals data. (Spending-over-time shipped 2026-06-16.)
- **Charts polish** — GUI eyeball of the new tabs (legend/colour/pie-label readability); decide whether the stacked over-time chart should also exclude Savings.
- **View tests** — The `qt-smoke` skill now provides a repeatable offscreen-Qt harness for ad-hoc view/dialog verification; automated pytest coverage of the PySide6 views themselves is still a possible follow-up (the non-UI modules and the fetcher QThreads are covered).
- **yfinance robustness** — Native socket timeouts are now in place (daemon-thread leak resolved). yfinance 1.3.0 also provides retry/backoff and 429 handling itself, so any *custom* retry layer is likely redundant — re-evaluate before building.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented.
- **Schema migrations** — No framework, but `init_db()` is the established migration point and the `db-migration` skill documents the procedure (additive columns, guarded idempotent data fixups, idempotent seeding). Column drop/rename is still manual SQL.

## License

Personal use. No license declared.
