---
name: new-feature
description: Build a new FinanceGuru feature end to end through the project's layered architecture — model, schema/migration, repository, view/dialog wiring, tests, and a headless smoke test — then commit. Use when the user says "new-feature", "add a feature", "build a feature", "scaffold a feature", "add a new tab/view/dialog", or "wire up X end to end".
---

# New Feature

Take a feature from request to a committed, verified change, moving through FinanceGuru's fixed layering so nothing is left half-wired. The architecture is strict and one-directional: **views → repositories → `db.get_connection()`**, with plain dataclass models and no ORM. This skill is the checklist that keeps a feature touching every layer it needs and no layer it doesn't.

It composes the other skills: hand schema work to `db-migration`, prove the UI with `qt-smoke`, and run `audit` before committing anything security- or money-sensitive.

## Before building

- **Scope it first.** Per CLAUDE.md, use `/interview` if the goal is fuzzy, and state a `/verify` plan up front — name the exact checks (pytest, qt-smoke, running the app) you'll use to call it done.
- **Run the parallelization check.** If the feature has independent pieces (e.g. researching two unrelated areas, or drafting files whose contents don't reference each other), fan out sub-agents. Keep coupled pieces (a new file and the line that imports it) together.

## Layers — build in this order

Each layer depends on the one before it, so build bottom-up.

1. **Model** — `src/financeguru/models/<thing>.py`. A plain `@dataclass`, money fields typed `Decimal`, `id: Optional[int] = None` last (matches `Expense`, `Bill`). No behavior.

2. **Schema** — if the feature needs a new table or column, **invoke the `db-migration` skill** rather than hand-editing `db.py`. It covers `init_db()` ordering, idempotent migrations for existing DBs, free-text re-tagging, and the `_CORE_TABLES` rule. If the feature stores nothing new, skip this layer.

3. **Repository** — `src/financeguru/repositories/<things>.py`, one module per model. Functions only (`get_all`, `add`, `update`, `delete`, plus any aggregate like `total_for_month`); open `with get_connection() as conn:` per call, parameterize every query, map rows with a private `_row_to_<thing>(row)` using `to_decimal()` for money. Never let SQL touch a view.

4. **Dialog** — `src/financeguru/views/<thing>_dialog.py` if the feature has an add/edit form. A `QDialog` with a `QFormLayout`, a `_prefill()` for edit mode, and a getter (`def <thing>(self) -> Model`) that returns a model built with `cents()` for money. Read dynamic option lists (categories, etc.) from their repository at construction time so they stay live.

5. **View** — a `QWidget` tab in `src/financeguru/views/`. Table + button bar pattern (see `expenses_view.py`): `Add/Edit/Delete` buttons disabled until a row is selected, a public `refresh()` that re-reads from the repository, `attach_row_menu(...)` for the context menu. Buttons call the dialog, then the repository, then `refresh()`.

6. **Wire into the window** — register the view in `views/main_window.py` (`self._tabs.addTab(...)`). The window's `_refresh_all()` / `_on_tab_changed()` call any `refresh()` automatically, so expose that method.

7. **Reporting/budget hooks** — if the feature affects money totals, update the relevant aggregator (`reporting.py` for per-category/per-month, `budget.py` for income/bill normalization, `salary_view.py` for the savings calculator) and keep `categories.py`'s constants as the single source of truth.

## Verify, then commit

8. **Tests** — add `tests/test_<thing>.py` in the house style: the `temp_db` fixture gives each test a fresh DB, so call repositories directly and assert round-trips (Decimal in/out, defaults, ordering, delete). Run them in the dev shell:
   ```bash
   nix develop --command python -m pytest -q
   ```

9. **Smoke the UI** — invoke `qt-smoke` to headlessly construct the new view/dialog against a throwaway DB, seed a row, and assert observable state (table contents, a computed label, a getter). GUI wiring isn't proven by pytest alone.

10. **Audit if warranted** — for anything touching money math, file I/O, backup/restore, or external data, run `audit` before committing.

11. **Commit** — only when asked, on a branch if on `main`. Conventional-commit subject (`feat(<area>): …`), summarize what each layer added and the test/smoke results, end with the `Co-Authored-By` trailer. Don't push unless asked.

## Gotchas

- **Respect the one-way dependency** — views call repositories, repositories call `get_connection()`. A view that runs SQL, or a model with behavior, breaks the layering the rest of the codebase relies on.
- **Don't hand-edit `db.py`** — route every schema change through `db-migration` so the existing-database path is handled.
- **Money is `Decimal` end to end** — `cents()` when reading from a spinbox, `to_decimal()` when reading from a row; the DB stores `REAL`.
- **Expose `refresh()`** on any view, or it won't update when the user switches tabs or after a backup restore.
- **Read dynamic lists at dialog open**, not import time, so newly added options (categories) appear without a restart.
- **Everything Python runs in `nix develop`** — PySide6 only exists there; LSP import errors outside the shell are expected.
