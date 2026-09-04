# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments and one-off expenses, monitors a stock portfolio with live prices, provides analyst-backed stock tips, calculates debt payoff strategies, visualizes an income budget with savings projections, plans savings goals with automatic monthly bill creation, converts between world currencies at live rates, keeps freeform monthly notes cross-linked to bills and goals, and charts where the money goes month to month. Database backup, restore, and CSV export are built into the File menu. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — twelve tabs fully implemented, ordered alphabetically with Dashboard pinned first (Dashboard, Bills, Charts, Currency Converter, Debt Snowball, Expenses, Goals, Income, Notes, Payments, Stock Tips, Stocks). All features are functional and persisted to SQLite. Every table across the app supports **click-to-sort headers**, and a **global month selector** in a toolbar above the tabs (new 2026-09-03) drives Bills, Payments, Expenses, Income, Goals, Notes, and the Charts pie chart from one always-visible picker, replacing what used to be seven separate per-tab dropdowns. The new **Notes** tab (also 2026-09-03) holds freeform journal entries filed under a calendar month, each optionally linked to a Bill or Goal with a clickable cross-tab jump. Income records each paycheck as a dated entry rather than a recurring day-of-month, and Goals track a start date so the required monthly contribution is fixed at creation time. The **Currency Converter** tab converts between ~31 major world currencies at live rates from the free Frankfurter API, cached locally with an offline fallback. The Charts tab includes a **net-worth trend chart** drawn from the daily snapshots the app has been recording since 2026-07-02, rendered gap-honestly (no interpolation across days the app didn't run). The app records that snapshot and takes an automatic rotating backup at every launch. The app also ships beyond NixOS — a **Flatpak** build and native **Windows/macOS** builds (via PyInstaller) are produced on every push through CI (see Installation below); nothing beyond GitHub's hosted runners has verified the Windows/macOS/Flatpak builds yet, so treat those as CI-verified, not hardware-verified. The flake's outputs are generated for both `x86_64-linux` and `aarch64-linux`. The app is installed as a NixOS system package on the `gaming` and `natalie-laptop` hosts and launches from the system app menu with a custom icon. A 328-test pytest suite covers the repositories, models, the `db`/`snowball`/`budget`/`prices`/`rates`/`reporting`/`categories`/`snapshots`/`notes` modules, the dashboard's overdue-bill rules, sortable-table row-identity behavior, offscreen smoke tests of every view, behavioral tests of the filter/gating/cross-tab-navigation views, and OS-path parity for the cross-platform builds. A full-diff code review is now standard practice before merging a cross-cutting feature PR — the most recent, on the Notes/global-selector PR, found and fixed one real cross-tab staleness bug pre-merge (9 lower-priority findings deliberately deferred as a backlog).

## Features

- **Dashboard** — Bills actually due this month with Paid / Overdue / Upcoming status badges and a monthly cost summary. Monthly bills appear every month, yearly bills only in their due month, and one-time bills only in their exact month and year. Unpaid one-time and yearly bills from past months are carried over as "Overdue (Month)" rows until paid — they never silently vanish — and count toward the Total/Remaining summary. Auto-refreshes on tab focus.
- **Net-worth snapshots** — A daily snapshot (stock value, debt total, goal savings, net worth) is recorded automatically at launch and updated after a full price refresh; the Charts tab's Net Worth view draws this history. One row per day; past rows are immutable.
- **Automatic backups** — A rotating daily backup is written at every launch (before any schema migration runs, so a bad migration is always recoverable) to a `backups/` folder alongside the database (see Configuration below for the OS-specific location), keeping the newest 14. Manual pre-restore safety copies are never pruned.
- **Global Month Selector** — One `QComboBox` in a toolbar row above the tabs, always visible regardless of which tab is active, drives Bills, Payments, Expenses, Income, Goals, Notes, and the Charts pie chart. Its entry list is the union of every one of those tabs' own "interesting months," rebuilt whenever a tab is switched to or the database is restored. Bills and Goals fall back to "All" if the selected month has nothing to show for that specific tab; Notes and the Charts pie chart have no "All" state (there's nothing to show for an unfiltered journal entry or a single-month snapshot) and simply keep their last specific month.
- **Notes** — Freeform journal entries filed under whichever month is selected in the global picker (so backfilling a past month works), newest-first. Optionally link a note to a single Bill or Goal; a linked note shows a "→ Name" indicator that jumps to that tab and drives the global selector to the linked item's own relevant month. Deleting a linked Bill or Goal offers to delete its linked notes too (Yes/No/Cancel), including notes linked via a Goal's own auto-created bill.
- **Bills** — Full CRUD for recurring bills (name, amount, due day, recurrence, category). Recurrence is schedule-aware: `monthly` bills recur every month, `yearly` bills carry a due month, and `one-time` bills carry a full due month + year (the dialog reveals the right pickers per recurrence). Mark Paid creates a linked payment record. Deleting a bill cascades to its payments. Filtered by the global month selector (defaulting to the current month); a Goal's auto-created bill additionally stays hidden until its start date is reached.
- **Payments** — Full payment history log sorted newest-first. Payments optionally reference a bill. Add, Edit (button or double-click), and Delete supported. Scoped by the global month selector (defaulting to the current month, with an "All" entry for full history). A live search bar filters by bill name, amount, date, or notes.
- **Expenses** — Log one-off, non-recurring expenses (amount, date, category, notes) with full Add/Edit/Delete CRUD, double-click to edit, and a right-click context menu. Scoped by the global month selector (defaulting to the current month, "All" for full history), and a live search bar filters by amount, date, category, or notes — the same filter pair as the Payments tab. Categories are **user-managed**: a "Manage Categories…" button opens a dialog to add, rename, and delete categories (seeded with Housing, Utilities, Groceries, Restaurants, Transport, Health, Entertainment, Pets, Savings, Other). Savings and Other are protected (the reporting layer depends on them) and can't be renamed or deleted.
- **Charts** — Two sub-tabs. *Spending* visualizes the trailing 12 months: a stacked bar chart breaks each month's spending into categories, and a pie chart shows a single month's breakdown, scoped by the global month selector (defaults to the current month). Spending = all payments + all expenses; goal contributions (payments against a goal-linked bill, identified by the goals foreign key) are counted as "Savings" and excluded from the monthly spending total. *Net Worth* draws the daily snapshot history as a date-axis line chart — contiguous runs of snapshots (≤7 days apart) connect into lines, every snapshot is dotted, and longer gaps render as visible breaks rather than interpolated lines. Auto-refreshes on tab focus.
- **Stocks** — Portfolio holdings with ticker, shares, purchase price, date, total cost basis, and live market price / market value / gain-loss fetched via yfinance. Green/red gain-loss colouring. Refresh Prices button triggers a background QThread fetch.
- **Stock Tips** — Track personal tips (ticker, action, target price, confidence, notes). Refresh Analyst Data fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- **Debt Snowball** — Track debts (balance, APR, minimum payment). A pure-Python month-by-month simulator computes both Snowball and Avalanche payoff strategies with rolling extra payments. Side-by-side summary shows total interest paid and time saved per strategy. A per-debt monthly payment schedule table shows exactly how each month's payment is allocated. One-time lump-sum extra payments (windfalls, bonuses, tax refunds) can be injected at a specific month and cascade across debts.
- **Income** — Log each paycheck as a dated entry (amount + calendar date), just like Payments/Expenses. Scoped by the global month selector, defaulting to the current month with an "All" entry for lifetime totals. The Monthly Budget summary subtracts monthly bills (shown as N/A in "All" scope, since it's a recurring figure with no honest all-time equivalent) and the selected scope's logged expenses to show the "Extra Spending Money" actually left over. A savings-rate slider splits that remainder into a proportional save-vs-spend bar with monthly and annual projections.
- **Goals** — Enter a savings goal (name, total price, start date, target month). The app computes the required monthly contribution (`price / months_remaining` from the start date, rounded up to the cent — fixed at creation/edit time rather than drifting as time passes) and auto-creates a recurring "Goal" bill so the commitment appears in the Bills and Dashboard tabs. Editing a goal updates its linked bill; deleting a goal (with confirmation) offers to delete linked notes too and deletes its linked bill. An "Amount Left" column tracks how much of the goal price remains unfunded as payments accumulate. The "Afford By" date always snaps to the last day of the chosen month.
- **Currency Converter** — Convert between ~31 major world currencies, each listed as "Name (Country)" (e.g. "Pound (England)"). Enter an amount, pick From/To currencies (or swap them), and see the converted result instantly. Rates come from the free, keyless Frankfurter API and are cached locally with a `fetched_at` date; offline, the tab falls back to the last-cached rates and says so ("Rates as of `<date>`"). Rates refresh automatically once per day and on demand via a "Refresh Rates" button. The last-used From/To currencies and amount are remembered across restarts.
- **Sortable tables** — Every data table (Dashboard, Bills, Payments, Expenses, Income, Stocks, Stock Tips, Goals, and Debt Snowball's debts/lump-sum tables) supports click-to-sort column headers with ascending/descending toggle; money, numeric, and non-ISO-date columns sort by their real value, not display text. Debt Snowball's payoff-plan comparison and monthly amortization schedule stay in computed, time order.
- **Right-click context menus** — The data tables (Bills, Payments, Expenses, Income, Stocks, Stock Tips, Debt Snowball, Goals) support right-click context menus mirroring their toolbar buttons. Right-clicking selects the row under the cursor first; selection-dependent actions are disabled when nothing is selected.
- **File menu** — Backup Database (WAL-safe SQLite online backup API, `chmod 600` before write, date-stamped default filename), Restore Database (validates source carries all FinanceGuru core tables, writes a timestamped `.bak` safety copy, clears stale WAL sidecars, runs schema migrations, refreshes all tabs), Export to CSV (table identifiers validated, all cells — headers included — sanitized against formula injection, each file created `0600` so it's never briefly world-readable), and Quit (Ctrl+Q).
- **App icon** — Custom green-dollar SVG icon in the system app menu, window title bar, and taskbar. Loaded via `QIcon.fromTheme` with SVG fallback for dev mode. Correctly installed into the Nix store prefix.
- **NixOS packaging** — `buildPythonApplication` target in `flake.nix`; installs desktop entry and icon into the system prefix. Packages, checks, and devShells are generated per-system (`x86_64-linux` and `aarch64-linux`), so an ARM host can consume the flake unchanged.
- **CI** — four GitHub Actions jobs run on every push and pull request: `flake-check` (`nix flake check` — builds the package, runs the full pytest suite headlessly in the Nix sandbox, and actually launches the packaged binary under a virtual display to confirm its Qt runtime environment works); `flatpak-check` (builds and launches the Flatpak under Xvfb); `windows-package` and `macos-package` (PyInstaller builds on the real hosted runners, running the full pytest suite natively on each OS, then a headless smoke launch of the frozen build). All four upload their build artifact.

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

### Installation (Flatpak)

Download the `financeguru.flatpak` bundle from the latest [GitHub Actions run](https://github.com/CommanderBosko/FinanceGuru/actions) (or an attached Release asset, once one exists), then install it locally:

```bash
flatpak install --user financeguru.flatpak
flatpak run io.github.CommanderBosko.FinanceGuru
```

### Installation (Windows)

Download `financeguru-windows.zip` from the latest [GitHub Actions run](https://github.com/CommanderBosko/FinanceGuru/actions) (or an attached Release asset, once one exists), unzip it, and run `FinanceGuru.exe` inside.

The build isn't code-signed yet, so Windows will show a "Windows protected your PC" SmartScreen warning on first launch — this is expected for a new, low-download app, not a sign of a problem. Click **More info**, then **Run anyway**.

### Installation (macOS)

Download `financeguru-macos.zip` from the latest [GitHub Actions run](https://github.com/CommanderBosko/FinanceGuru/actions) (or an attached Release asset, once one exists), unzip it, and move `FinanceGuru.app` wherever you like (e.g. `/Applications`).

The build isn't notarized, so macOS will refuse to open it with a plain double-click ("FinanceGuru.app cannot be opened because it is from an unidentified developer"). Instead, right-click (or Control-click) the app and choose **Open**, then confirm in the dialog that appears. This is only needed once per machine. Note: `macos-latest` GitHub Actions runners are Apple Silicon (arm64) only, so this build targets Apple Silicon Macs.

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

The SQLite database is created automatically at first run, in the OS-appropriate per-user data directory (resolved via `platformdirs`, verified in CI on real Windows and macOS runners as well as Linux):

```
Linux:   ~/.local/share/financeguru/finance.db   (or $XDG_DATA_HOME/financeguru/finance.db if set)
Windows: %LOCALAPPDATA%\financeguru\finance.db
macOS:   ~/Library/Application Support/financeguru/finance.db
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
├── currencies.py                 # Currency Converter's ~31-currency list ("Name (Country)") + pivot-base constant
├── rates.py                      # RatesFetcher QThread — background Frankfurter API lookups, bounded-then-unbounded teardown
├── models/
│   ├── bill.py                   # Bill dataclass (with category)
│   ├── payment.py                # Payment dataclass
│   ├── expense.py                # Expense dataclass (one-off spending with category)
│   ├── stock.py                  # Stock dataclass
│   ├── stock_tip.py              # StockTip dataclass
│   ├── debt.py                   # Debt dataclass
│   ├── income.py                 # Income dataclass (dated paycheck: amount + pay_date)
│   ├── goal.py                   # Goal dataclass + months_remaining() + monthly_savings()
│   ├── category.py               # Category dataclass (name, position, is_protected)
│   ├── snapshot.py               # Snapshot dataclass (daily net-worth record)
│   ├── currency_rates.py         # CurrencyRates dataclass (base, rates, fetched_at)
│   └── note.py                   # Note dataclass (body, month_year, created_at, optional bill_id/goal_id)
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
│   ├── snapshots.py              # Daily net-worth snapshot capture (launch + post-price-refresh upsert)
│   ├── currency_rates.py         # DB cache for the fetched Frankfurter rate table (singleton per base currency)
│   ├── preferences.py            # Generic key/value settings table (get/set/set_many) — first used by Currency Converter
│   └── notes.py                  # DB access for notes (CRUD, get_for_month, earliest_month, get_by_bill_id/get_by_goal_id)
└── views/
    ├── main_window.py            # QMainWindow with QTabWidget + File menu + global month-selector toolbar; refreshes all tabs on focus/restore
    ├── context_menu.py           # Reusable attach_row_menu helper for right-click table menus
    ├── dashboard_view.py         # Monthly bill status summary
    ├── bill_dialog.py            # Add/Edit bill form
    ├── bills_view.py             # Bills tab — table + Add/Edit/Delete/Mark Paid + select_month/select_all/month_keys + goal-bill gating
    ├── payment_dialog.py         # Log payment form
    ├── payments_view.py          # Payments tab — history + Add/Edit/Delete + select_month/select_all/month_keys + search
    ├── expense_dialog.py         # Add/Edit one-off expense form
    ├── expenses_view.py          # Expenses tab — table + Add/Edit/Delete + Manage Categories
    ├── category_dialog.py        # Manage Categories dialog (add/rename/delete; protects Savings/Other)
    ├── note_dialog.py            # Add/Edit note form (body + optional Bill/Goal link picker)
    ├── notes_view.py             # Notes tab — journal entries + Add/Edit/Delete + link-click cross-tab navigation
    ├── _month_filter.py          # Shared month/year dropdown mechanics (month_entries/populate_from_keys) behind each tab's select_month/select_all/month_keys contract
    ├── charts_view.py            # Charts tab — Spending (stacked bars + pie) and Net Worth (trend line) sub-tabs (QtCharts)
    ├── currency_converter_view.py # Currency Converter tab — amount/from/to/swap, live rates + cached fallback
    ├── _table.py                 # Shared table-cell builders (right/center/SortableItem) + the money() display formatter
    ├── stock_dialog.py           # Add/Edit stock holding form
    ├── stocks_view.py            # Stocks tab — holdings table + live prices
    ├── stock_tip_dialog.py       # Add/Edit stock tip form
    ├── stock_tips_view.py        # Stock Tips tab — tips table + analyst data refresh
    ├── debt_dialog.py            # Add/Edit debt form
    ├── debt_snowball_view.py     # Debt Snowball tab — CRUD + simulation + schedule + lump sums
    ├── income_dialog.py          # Add/Edit income form (amount + calendar date picker)
    ├── salary_view.py            # Income tab — income list + budget visualizer + savings slider
    ├── goal_dialog.py            # Add/Edit goal form with live monthly-savings preview
    └── goals_view.py             # Goals tab — goal table + bill sync + Amount Left tracking
share/
├── applications/
│   └── financeguru.desktop       # XDG desktop entry for app menu
└── icons/hicolor/
    ├── scalable/apps/financeguru.svg    # Custom green-dollar app icon (Nix/dev/Flatpak fallback)
    └── 128x128/apps/financeguru.png     # Rasterized icon (Flatpak AppStream export, PyInstaller .ico/.icns source)
packaging/
├── flatpak/
│   ├── io.github.CommanderBosko.FinanceGuru.yml           # Flatpak manifest
│   └── io.github.CommanderBosko.FinanceGuru.metainfo.xml  # AppStream metadata
└── pyinstaller/
    ├── requirements.txt           # Build-only deps (pyinstaller, pillow) — not a runtime dependency
    ├── make_icons.py              # Generates .ico/.icns from the 128x128 PNG
    ├── financeguru.spec           # Single spec, sys.platform-branched, drives both Windows and macOS
    └── smoke_launch.py            # Cross-platform headless launch-and-stay-alive check (no GNU timeout/xvfb-run needed)
.github/workflows/
└── ci.yml                        # GitHub Actions — flake-check, flatpak-check, windows-package, macos-package
```

## Recent Changes

**2026-09-03 — Notes Tab + Global Month Selector**

- **New Notes tab** — freeform journal entries filed under a calendar month, optionally linked to a single Bill or Goal with a clickable cross-tab jump to the linked item's own relevant month. Deleting a linked Bill/Goal offers to delete its notes too.
- **Global month selector** — one toolbar picker above the tabs now drives Bills, Payments, Expenses, Income, Goals, Notes, and the Charts pie chart, replacing what used to be seven separate per-tab dropdowns; each tab still applies its own filtering rule behind a shared `select_month`/`select_all`/`month_keys` contract.
- A pre-merge full-diff code review on the whole PR caught and fixed a real bug where following a note's cross-month link left other tabs showing a stale month next to the toolbar, plus a pre-existing gap where a Goal's mirrored-bill-linked notes weren't counted or deleted by the Goals delete-cascade prompt. 9 lower-priority findings from that same review were deliberately deferred as a follow-up backlog (see Roadmap). Suite 240 → 328 tests, all green.

**2026-08-31 — Skill-Library Maintenance (Internal)**

- Internal only, no user-facing changes: the `manager` agent ran a full `/improve-system` pass (skill-upgrade, skill-suggestion, agent-suggestion, claude-rules, skill-audit, fewer-permission-prompts) and landed it as PR #2. Fixed a real bug in the `qt-visual-verify` skill's documented headless-screenshot command (it was silently rendering on-screen instead of offscreen), plus two smaller skill-audit findings (a data-mutating decision in `db-migration` now requires explicit confirmation; a doc/script duplication in `secret-scan` removed). Suite unchanged at 240 tests.

**2026-08-16 — Currency Converter Tab + Tab Reorder**

- **New Currency Converter tab** — convert between ~31 major world currencies ("Name (Country)" format), with live rates from the free Frankfurter API, a local cache with an offline fallback, and last-used From/To/amount remembered across restarts.
- **Tabs reordered alphabetically, Dashboard pinned first** — Dashboard, Bills, Charts, Currency Converter, Debt Snowball, Expenses, Goals, Income, Payments, Stock Tips, Stocks.
- An `/audit` pass fixed 9 issues, including a QThread-teardown crash risk on quit and `refresh()` not correctly reloading state after a DB restore. Suite 210 → 240 tests, all green.

**2026-08-03 — Bills Month/Year Filter, Windows CI Fix, qt-visual-verify Skill**

- **Bills tab gained a month/year filter** (matching Payments/Income), and a Goal's auto-created bill now stays hidden until its start date is reached, fixing a bug where future-dated goals showed up on Bills immediately.
- **Fixed a Windows-only crash** in CSV export (`os.O_NOFOLLOW` doesn't exist on that platform) — caught by real Windows CI, not local testing.
- Internal: added the `qt-visual-verify` project skill (screenshot-based visual verification) and committed the repo's own `.gitignore` rule for `.claude/settings.local.json`. Suite 201 → 210 tests, all green.

**2026-08-02 — Month Filters, Sortable Headers, Income Redesign, Goals Start Date, Audit Fixes**

- **Month/year dropdown filters** — Payments and Expenses both moved from a "This month only" checkbox to a shared dropdown (`views/_month_filter.py`) spanning "All" plus every month back to the earliest record.
- **Sortable table headers everywhere** — every data table now supports click-to-sort with ascending/descending toggle, with correct numeric/date ordering rather than alphabetical. Fixed a latent bug along the way: row selection now reads each row's identity off the table item itself rather than a table-position index, since the latter silently breaks once sorting can reorder rows.
- **Income is now a dated paycheck log** — after briefly consolidating to a single recurring pay-day, Income switched to a real `pay_date` per entry (matching Payments/Expenses) so it could get the same month/year dropdown and support irregular income. The upgrade migration clears pre-existing income rows, since they predate real dates.
- **Goals track a start date** — the required monthly contribution is now fixed when a goal is created or edited (`start_date → target_date`) instead of recalculating against today's date every time the app is opened.
- **Audit pass fixed 3 real bugs**: a crash risk where the row context menu's refresh action could destroy an in-flight background fetch thread on Stocks/Stock Tips; a Salary "All-time" view showing a nonsensical budget figure; and category renames not updating existing bills/expenses that used the old name. Suite 180 → 201 tests, all green.

**2026-07-26 — Cross-Platform Packaging: Flatpak + Windows + macOS**

- **Flatpak** — a manifest built on `io.qt.PySide.BaseApp`/`org.kde.Platform`, verified with a real local `flatpak-builder` build → export → bundle → install → launch, plus a CI job that builds and launches it under Xvfb on every push.
- **Windows and macOS** — a single PyInstaller spec (branched on `sys.platform`) builds and headlessly smoke-launches native packages for both, entirely on GitHub's hosted runners since no Windows/Mac hardware exists locally. See Installation above for the expected SmartScreen/Gatekeeper first-run steps on an unsigned build.
- **Database location is now OS-appropriate** everywhere, resolved via `platformdirs` (Linux path unchanged, so existing installs aren't affected).
- Three bugs surfaced only by watching the real CI runs (never reproducible locally): missing `flatpak-builder`/`pytest` installs on the runner, a deprecated Flatpak Action needing a maintained replacement, and a Windows path-resolution test that needed rewriting against the real `LOCALAPPDATA` rather than an env-var override. Suite 160 → 163 tests, all green.

**2026-07-26 — Skill-Library Maintenance (Internal)**

- Internal only, no user-facing changes: added a new `watch-ci` Claude-skill to babysit GitHub Actions runs after a push, and fixed 4 issues (2 real bugs, 2 structural) found by an immediate audit of all 9 project-local skills.

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
- **Global-selector follow-ups** — a prioritized backlog of 9 findings deferred from the pre-merge review of the Notes/global-month-selector PR (details in project memory / `project-state.md`). The two highest-value: make a Goal-with-mirrored-Bill delete atomic (currently two separate transactions), and have month-aware tabs notify `MainWindow` after their own Add/Edit/Delete so the global month list updates without needing a tab switch.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented, and the two machines hold two independent SQLite files (a sync-vs-partition decision to make deliberately first).
- **Schema migrations** — No framework, but `init_db()` is the established migration point and the `db-migration` skill documents the procedure (additive columns, guarded idempotent data fixups, idempotent seeding). Column drop/rename is still manual SQL.

## License

MIT — see [LICENSE](LICENSE).
