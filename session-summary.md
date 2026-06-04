# Session Summary — Finance Guru

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
