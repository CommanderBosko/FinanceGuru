# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FinanceGuru is a personal finance desktop app for two users (bosko and natty). Feature areas:

1. **Bills** — recurring bill tracking and due dates
2. **Payments** — payment history and logging
3. **Stocks** — portfolio tracking
4. **Stock tips** — recommendations (planned future phase)

## Tech Stack

- **GUI:** PySide6 (Qt6)
- **Database:** SQLite via `sqlite3` stdlib — file at `~/.local/share/financeguru/finance.db`
- **Python:** 3.12, source layout under `src/financeguru/`
- **Environment:** Nix flake — all deps declared in `flake.nix`

## Common Commands

```bash
# Enter the dev environment (required before running anything)
nix develop

# Run the app
python -m financeguru.main

# Run tests
python -m pytest

# Lock flake inputs after adding a new dependency
nix flake update
```

## Architecture

```
src/financeguru/
├── main.py          # Entry point — init_db(), QApplication, MainWindow
├── db.py            # SQLite connection, schema creation (init_db)
├── models/          # Plain dataclasses: Bill, Payment, Stock
└── views/
    ├── main_window.py   # QMainWindow with QTabWidget (Bills / Payments / Stocks)
    ├── bills_view.py
    ├── payments_view.py
    └── stocks_view.py
```

Database schema lives in `db.py:init_db()` as a single `executescript`. No ORM — raw `sqlite3` with `row_factory = sqlite3.Row`. Foreign keys are enabled per connection.

## NixOS Integration

Once the app is functional, wire it into `~/NixOS/flake.nix` as an input:

```nix
financeguru.url = "github:CommanderBosko/FinanceGuru";
```

Then add `inputs.financeguru.packages.x86_64-linux.default` to `environment.systemPackages` in the relevant host's `environment.nix`. The `qt6.wrapQtAppsHook` in `flake.nix` handles Qt plugin paths at install time.

## Notes

- PySide6 import errors from the LSP are expected — the package only exists inside `nix develop`, not the system Python.
- `QT_QPA_PLATFORM=wayland;xcb` is set in the devShell to handle both Wayland and X11 fallback across the three desktop machines (Plasma, Niri, Cosmic).
