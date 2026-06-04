# Finance Guru

A personal finance desktop application for two users (bosko and natty). Tracks recurring bills, logs payments, monitors a stock portfolio with live prices, and provides a daily-at-a-glance dashboard. Built with PySide6 and SQLite, packaged as a Nix flake.

## Current Status

Active development — v0.1.0, first full working version. All four planned tabs are implemented (Dashboard, Bills, Payments, Stocks). The app launches from the system app menu on NixOS and carries a custom icon in the title bar and taskbar.

## Features

- **Dashboard** — Shows all bills due this month with Paid / Overdue / Upcoming status badges and a monthly cost summary. Auto-refreshes when the tab is focused.
- **Bills** — Full CRUD for recurring bills (name, amount, due day, frequency). Mark Paid action creates a payment record. Cascade-deletes linked payments on bill removal.
- **Payments** — Log and view full payment history sorted newest-first. Payments can optionally reference a bill. Add and Delete supported.
- **Stocks** — Portfolio holdings table with ticker, shares, purchase price, date, total cost basis, and live market price / market value / gain-loss fetched via yfinance. Green/red colouring for gain/loss. Refresh Prices button triggers background fetch via QThread.
- **App icon** — Custom green-dollar SVG icon in the system app menu, title bar, and taskbar. Loaded via `QIcon.fromTheme` with SVG fallback for dev mode.
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

No manual configuration is required.

## Project Structure

```
src/financeguru/
├── main.py                  # Entry point — init_db(), QApplication, MainWindow
├── db.py                    # SQLite connection + schema (init_db); row_factory=sqlite3.Row
├── prices.py                # PriceFetcher QThread — background yfinance price lookup
├── models/
│   ├── bill.py              # Bill dataclass
│   ├── payment.py           # Payment dataclass
│   └── stock.py             # Stock dataclass
├── repositories/
│   ├── bills.py             # DB access for bills
│   ├── payments.py          # DB access for payments
│   └── stocks.py            # DB access for stocks
└── views/
    ├── main_window.py       # QMainWindow with QTabWidget; refreshes Dashboard on tab switch
    ├── dashboard_view.py    # Monthly bill status summary
    ├── bill_dialog.py       # Add/Edit bill form
    ├── bills_view.py        # Bills tab — table + Add/Edit/Delete/Mark Paid
    ├── payment_dialog.py    # Log payment form
    ├── payments_view.py     # Payments tab — history + Add/Delete
    ├── stock_dialog.py      # Add/Edit stock holding form
    └── stocks_view.py       # Stocks tab — holdings table + live prices
share/
├── applications/
│   └── financeguru.desktop  # XDG desktop entry for app menu
└── icons/hicolor/scalable/apps/
    └── financeguru.svg      # Custom green-dollar app icon
```

## Recent Changes

**2026-06-04 — Project inception and full initial build**

- Scaffolded the entire project from scratch: Nix flake, pyproject.toml, SQLite schema, dataclasses, repository layer, and tabbed UI.
- Implemented Bills tab with full CRUD and Mark Paid.
- Implemented Payments tab with history log and Add/Delete.
- Implemented Stocks tab with holdings tracking and live price refresh via yfinance/QThread.
- Added Dashboard tab with monthly bill status overview.
- Fixed multiple Nix packaging issues (flake.nix syntax, buildInputs, build backend).
- Added XDG desktop entry so the app appears in the system app menu.
- Created custom SVG icon; wired it into the desktop entry and the window title bar/taskbar.
- Corrected title bar text from "FinanceGuru" to "Finance Guru".

## Roadmap

- **Stock Tips tab** — Planned fourth feature area; recommendations and notes per ticker.
- **NixOS integration** — Wire `financeguru.url` input into `~/NixOS/flake.nix` and add to a host's `environment.systemPackages`.
- **Tests** — `tests/` directory exists but is empty; add repository and view unit tests.
- **Schema migrations** — Current approach requires manual handling of existing DBs when columns are added; consider a lightweight migration utility.
- **Multi-user support** — App is used by two people (bosko, natty); per-user data partitioning is not yet implemented.

## License

Personal use. No license declared.
