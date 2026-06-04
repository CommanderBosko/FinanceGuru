# Project State — Finance Guru

_Last updated: 2026-06-04_

## Current Project State

The app is fully functional for its first four feature areas. All tabs — Dashboard, Bills, Payments, Stocks — are implemented and operational. The Nix flake builds a system package, installs the XDG desktop entry, and the custom icon appears in the app menu, title bar, and taskbar. The working tree is clean and all commits are pushed to `origin/main`.

**What works:**
- Full Bills CRUD with Mark Paid (creates a linked Payment record; cascade-delete on bill removal)
- Payment history log with Add and Delete
- Stock portfolio table with Add/Edit/Delete and live price refresh via yfinance QThread
- Dashboard showing monthly bill status (Paid / Overdue / Upcoming) with cost summary, auto-refreshing on tab focus
- App icon displayed in system app menu, window title bar, and taskbar
- Nix `buildPythonApplication` packaging with desktop entry and icon installed to prefix

**What is in progress / stub state:**
- `tests/` directory exists but contains no tests
- Stock Tips tab is planned but not started

**What is broken:**
- Nothing known

## Current Goals

### Short-term (next 1-3 sessions)
1. Wire the package into the NixOS flake at `~/NixOS/flake.nix` — add `financeguru.url` as an input and add the package to a host's `environment.systemPackages`.
2. Begin the Stock Tips tab (data model, repository, dialog, view).
3. Write initial tests for the repository layer (`bills.py`, `payments.py`, `stocks.py`).

### Long-term
- Multi-user data partitioning (bosko vs. natty views/profiles)
- Lightweight schema migration utility for adding columns to existing DBs
- Stock Tips feature fully implemented
- Evaluate adding a budget / spending-over-time view

## Recent Decisions

- **No ORM** — Direct `sqlite3` calls via a thin repository layer. Keeps the dependency list minimal and the query intent explicit.
- **QThread for price fetching** — Avoids blocking the UI during yfinance network calls; `PriceFetcher` in `prices.py` emits a signal when done.
- **`QIcon.fromTheme` + SVG fallback** — Works correctly both as a NixOS system package (where the theme icon is registered) and in `nix develop` dev mode (falls back to the SVG path relative to the source tree).
- **Single `executescript` schema** — All DDL lives in `db.py:init_db()`. Simple and easy to read; schema migrations require manual intervention on existing DBs.
- **`buildPythonApplication` in flake.nix** — Chose this over a wrapper script so the app gets proper Qt plugin paths via `qt6.wrapQtAppsHook` at install time.

## Known Issues / Tech Debt

- No tests exist yet (`tests/` is an empty stub).
- No schema migration strategy — adding columns to an existing `finance.db` requires manual SQL or a drop-and-recreate.
- Multi-user support is not implemented; both users share the same SQLite file at `~/.local/share/financeguru/finance.db`.
- Stock price fetching depends on yfinance / Yahoo Finance availability; no error handling for rate-limiting or network failure beyond a silent no-op.

## Next Steps

1. Add `financeguru` as a NixOS flake input in `~/NixOS/flake.nix` and install to a host.
2. Create the `StockTip` model, `stock_tips` repository, `StockTipDialog`, and `StockTipsView` — wire as a fifth tab.
3. Add repository-layer pytest tests using an in-memory SQLite database.
4. Add error handling/user-visible feedback when yfinance price fetch fails.
