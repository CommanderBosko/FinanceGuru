# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Scope First (Interview)

Before you do any work, use the `/interview` skill to pin down the real goal with the user — don't start building from a fuzzy or assumed understanding of the request. Surface the unknowns, confirm scope and constraints, and only proceed once the target is clear. Do this in tandem with the Verification Plan below: the interview establishes *what* we're building and how we'll know it's done, and the verification plan establishes *how we'll prove* it works. Lay out both together, up front, before starting the work.

## Verification Plan

Before you do any work, state how you'll verify it with the `/verify` skill — say up front how you'll confirm each part actually works before calling it done. Pick the checks that fit this project (build, test suite, linter, type-check, running the app, hitting the endpoint, reading the logs) and name the specific commands. Lay out the plan with the work, not after it.

## Parallelize with Sub-Agents

**This rule is your standing authorization to spawn sub-agents — you do not need to ask first.** Once scope and the verification plan are set, before starting any task with more than one independent part, stop and run a parallelization check. This is a required step, not an aspiration: ask "Can I split this into pieces that don't depend on each other's output?" If yes, spawn one sub-agent per piece in a single message and let them run concurrently.

Trigger parallelization whenever you hit any of these:
- About to research, search, or read across 2+ areas of the tree that don't depend on each other.
- About to scaffold or draft 2+ files whose *contents* don't reference each other.
- You catch yourself planning "do A, then B, then C" where B doesn't need A's result.

Reserve serial work for genuine dependencies — e.g. a new file and the line elsewhere that imports it are coupled, so keep them together. When the pieces are independent, default to fanning out breadth-first; state in your plan which pieces run in parallel and why.

## Use Existing Skills First

Before doing a task by hand, check whether an existing skill already covers it and invoke it instead of improvising. Skills encode the agreed, repeatable way to do a thing — prefer them over ad-hoc steps. If you find yourself doing the same multi-step task a second time and no skill exists, offer to create one.

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
├── db.py            # SQLite connection + schema (init_db); row_factory=sqlite3.Row
├── models/          # Plain dataclasses: Bill, Payment, Stock
├── repositories/    # DB access layer — one module per model (bills, payments, stocks)
└── views/
    ├── main_window.py   # QMainWindow with QTabWidget (Bills / Payments / Stocks)
    ├── bill_dialog.py   # Add/Edit bill form (QDialog)
    ├── bills_view.py    # Bills tab — table + Add/Edit/Delete/Mark Paid
    ├── payments_view.py
    └── stocks_view.py
```

**Layers:** views call repositories; repositories call `db.get_connection()`; no ORM. Foreign keys are enabled per connection in `get_connection()`. Schema lives in `db.py:init_db()` as a single `executescript` — update it there when adding columns, then handle existing DBs manually or via a migration script.

## NixOS Integration

Once the app is functional, wire it into `~/NixOS/flake.nix` as an input:

```nix
financeguru.url = "github:CommanderBosko/FinanceGuru";
```

Then add `inputs.financeguru.packages.x86_64-linux.default` to `environment.systemPackages` in the relevant host's `environment.nix`. The `qt6.wrapQtAppsHook` in `flake.nix` handles Qt plugin paths at install time.

## Notes

- PySide6 import errors from the LSP are expected — the package only exists inside `nix develop`, not the system Python.
- `QT_QPA_PLATFORM=wayland;xcb` is set in the devShell to handle both Wayland and X11 fallback across the three desktop machines (Plasma, Niri, Cosmic).
