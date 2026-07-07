---
name: qt-smoke
description: Headlessly construct and exercise a FinanceGuru PySide6 view/dialog/MainWindow against a throwaway database to verify it works without launching the real app. Use when the user says "qt-smoke", "smoke test the GUI", "offscreen smoke test this view", "verify the dialog/widget loads", or "check the view renders without a display".
---

# Qt Smoke

Verify a PySide6 widget (a view, dialog, or `MainWindow`) actually constructs and behaves correctly — headless, against a temp database — without launching the real app or needing a display.

This fills a gap the other skills don't: `/run` launches the app with a real display, and `/verify` is generic. This drives the specific Qt-on-nix pattern FinanceGuru needs (Qt only exists inside `nix develop`, and we must never touch the user's real `finance.db`).

## Steps

1. **Figure out what to assert.** From the change under review, pick the concrete, observable behaviour to check — e.g. a dialog row's visibility per recurrence, the set of rows a table shows after seeding data, or that teardown (`stop_threads()` / `done()`) runs without aborting. If it's unclear, ask the user what "working" looks like for this widget.

2. **Write a single headless Python snippet** and run it with:
   ```bash
   QT_QPA_PLATFORM=offscreen nix develop --command python -c "..."
   ```
   `QT_QPA_PLATFORM=offscreen` renders Qt with no display; `nix develop` is required because PySide6 only exists in the dev shell.

3. **Redirect the database to a temp dir BEFORE `init_db()`, then create the app.** Read `assets/preamble.py` and prepend it verbatim to your script — it redirects `db.DB_DIR`/`db.DB_PATH` to a throwaway temp dir before `init_db()` (so real data is never touched) and constructs the `QApplication`. Don't retype this by hand; a skipped line (e.g. only setting `DB_PATH` and forgetting `DB_DIR`) breaks the isolation this skill exists to guarantee. `get_connection()` reads `db.DB_PATH` and `init_db()` makes `db.DB_DIR`.

4. **Construct the widget.** After the preamble, build the target: `MainWindow()`, `BillDialog()`, `DashboardView()`, etc. Seed any data first via the repositories (`from financeguru.repositories import bills as bill_repo; bill_repo.add(Bill(...))`).

5. **Drive the interaction and assert state.** Use plain `assert`s. Common probes:
   - Dialog row visibility: `dlg._form.isRowVisible(dlg._due_month)` after `dlg._recurrence.setCurrentText("yearly")`
   - Table contents: `{tbl.item(r, 0).text() for r in range(tbl.rowCount())}`
   - Computed getters: `dlg.bill()`, `dlg.goal()`
   - Teardown: `view.stop_threads()`, `dlg.done(0)`, `window.close()`
   Print `SMOKE OK` (optionally with the asserted value) on success; let an `AssertionError` surface and fail loudly.

6. **Run it and report.** Pipe through `| tail -10` to keep output tight. Report `SMOKE OK` plus what was verified, or the assertion/traceback if it failed.

## Worked example — dashboard + dialog (today's pattern)

The preamble below is `assets/preamble.py`'s content inlined (a `python -c` one-liner has to be a single self-contained script, so it can't `read` the asset file at runtime) — copy this whole example as your starting point rather than reassembling the preamble by hand.

```bash
QT_QPA_PLATFORM=offscreen nix develop --command python -c "
import tempfile, pathlib
from decimal import Decimal
from datetime import date
import financeguru.db as db
d = pathlib.Path(tempfile.mkdtemp()) / 'fg'
db.DB_DIR = d; db.DB_PATH = d / 'finance.db'; db.init_db()

from PySide6.QtWidgets import QApplication
from financeguru.models.bill import Bill
from financeguru.repositories import bills as bill_repo
from financeguru.views.bill_dialog import BillDialog
from financeguru.views.dashboard_view import DashboardView
app = QApplication([])

# Dialog: Due Month/Year rows appear only for the right recurrence.
dlg = BillDialog()
assert (dlg._form.isRowVisible(dlg._due_month), dlg._form.isRowVisible(dlg._due_year)) == (False, False)
dlg._recurrence.setCurrentText('one-time')
assert (dlg._form.isRowVisible(dlg._due_month), dlg._form.isRowVisible(dlg._due_year)) == (True, True)

# Dashboard: only bills due THIS month/year are listed.
y, m = date.today().year, date.today().month
bill_repo.add(Bill(name='Monthly', amount=Decimal('100'), due_day=1, recurrence='monthly'))
bill_repo.add(Bill(name='OnceNow', amount=Decimal('50'), due_day=5, due_month=m, due_year=y, recurrence='one-time'))
bill_repo.add(Bill(name='OncePast', amount=Decimal('70'), due_day=5, due_month=m, due_year=y-1, recurrence='one-time'))
shown = {(lambda t: {t.item(r,0).text() for r in range(t.rowCount())})(DashboardView()._bills_table)}
assert shown == {'Monthly', 'OnceNow'}, shown
print('SMOKE OK', shown)
" 2>&1 | tail -10
```

## Gotchas

- **PySide6 and yfinance only exist inside `nix develop`.** Outside the dev shell the import fails; LSP/Pyright "could not be resolved" errors for `PySide6.*` and `yfinance` are expected and not real problems.
- **Never run without the temp-DB redirect** — a bare `init_db()` writes to `~/.local/share/financeguru/finance.db`, the user's real data.
- **Stub the network for Stocks / Stock Tips refresh.** `StocksView._on_refresh` / `StockTipsView._on_refresh` start a real `PriceFetcher` / `TipFetcher` that hits Yahoo. To smoke those paths, monkeypatch the fetcher in the view module (e.g. `import financeguru.views.stocks_view as sv; sv.PriceFetcher = FakeFetcher`) or test the teardown branch (`stop_threads()`) directly instead of triggering a live fetch.
- **Prefer the pytest suite for pure logic.** This skill is for GUI wiring/behaviour that needs a live `QApplication`; model/repository/reporting logic belongs in `python -m pytest` (also run via `nix develop --command`).
