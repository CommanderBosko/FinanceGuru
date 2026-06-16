# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

## Session: 2026-06-15 — Test Coverage Beyond Repositories + Per-Ticker Fetch Feedback

**Focus**: Extend the pytest suite past the repository layer and surface yfinance per-ticker fetch failures to the user.

### What changed (and why)
- Confirmed (no code change) that the package is already wired into `~/NixOS/flake.nix` as an input and installed on both the `gaming` and `natalie-laptop` hosts — `project-state.md` had been carrying this as an open "top priority" for six sessions; it's done.
- Added four test modules (suite 36 → 69, all green): `test_db.py` (backup/restore/export-CSV/`_csv_safe`/`_ensure_column`), `test_snowball.py` (payoff, strategy ordering, extra/lump-sum, interest, empty), `test_budget.py` (all pay frequencies + `monthly_bill` recurrence), `test_prices.py` (`_call_with_timeout` plumbing). All reuse the existing autouse temp-file DB fixture.
- Surfaced per-ticker fetch failures: `_call_with_timeout` now returns `(ok, value)` so a genuine empty result (delisted ticker → `ok=True, value=None`) is distinct from a timeout/error. `PriceFetcher`/`TipFetcher` collect failed tickers and emit a new `partial_error` signal; both stock views warn naming exactly which tickers couldn't be fetched.

### Decisions
- **`(ok, value)` tuple over a sentinel** — the existing code returned `None` for both "no data" and "fetch failed", so the two were indistinguishable. A boolean `ok` is the minimal change that lets the view decide whether to warn, and keeps `value` free to be a legitimate `None`.
- **`partial_error` is a separate signal from `fetch_error`** — `fetch_error` means the whole fetch collapsed (e.g. yfinance import failed); `partial_error` means some tickers came back but others timed out. Different user messages, so different signals.
- **Views stay untested for now** — extended coverage to the remaining pure modules; the PySide6 views need an offscreen-Qt harness, deferred as optional.

### Issues / surprises
- None. `_call_with_timeout`'s type change surfaced two Pyright `reportArgumentType` errors; fixed by making the helper generic (`Callable[[], _T] -> tuple[bool, _T | None]`).

### Next session
- Fix leaked daemon threads in `prices.py` (inject a `requests.Session` with native socket timeouts).
- Add structured retry / rate-limit backoff for yfinance fetches.

**Commits**: `43c4199` (1 commit) + this session-close

---

## Session: 2026-06-07 (Night #2) — Security Audit #2: CSV Injection, Restore Safety, File Perms

**Duration Estimate**: Single focused session
**Session Focus**: Second comprehensive security audit of the ~3,500-line codebase (all new features added since the first audit: Goals, Debt Snowball, Income/Salary, Stock Tips, File menu with Backup/Restore/Export CSV, context menus, search). Findings triaged by severity and all actionable items fixed and pushed.

### What Was Accomplished

- Parallelized the audit across three sub-agents: data layer (DB access, SQL, schema), network/dependencies (yfinance, prices.py, pyproject.toml), and file operations (backup, restore, CSV export, permissions).
- **CRITICAL fix — CSV/formula injection** (`db.py`): Added `_csv_safe()` helper that prefixes cells beginning with `=`, `+`, `-`, `@`, TAB, or CR with a literal apostrophe, neutralizing spreadsheet formula execution when exported CSVs are opened in Excel or LibreOffice Calc.
- **MEDIUM fix — Restore safety** (`db.py`): `restore_database()` now rejects any source file that lacks the FinanceGuru core tables (`bills`, `payments`, `stocks`, `incomes`, `debts`, `goals`, `stock_tips`), giving a clear error message instead of silently overwriting the live database with an unrelated SQLite file. Also writes a timestamped `.pre-restore-YYYYMMDD-HHMMSS.bak` copy of the current database before overwriting, and calls `init_db()` after restore so backups from older app versions gain any schema columns added since.
- **MEDIUM fix — Export identifier hardening** (`db.py`): Table names from `sqlite_master` are now validated with `_IDENT_RE.fullmatch()` before being interpolated into SQL or used as filenames. Tables with non-identifier characters are skipped, blocking SQL injection and path traversal from a crafted/restored database.
- **LOW fix — Backup file permissions** (`db.py`): `backup_database()` now `chmod 0o600`s the destination file before the SQLite backup writes into it, so the backup is never momentarily world-readable on multi-user machines.
- **LOW fix — CSV file permissions** (`db.py`): Each exported CSV file is `chmod 0o600` after writing; the CSVs hold the same plaintext financial data as the database.
- **LOW fix — Price fetch error hygiene** (`prices.py`): `PriceFetcher` and `TipFetcher` no longer surface raw exception messages (which can contain URLs, hostnames, proxy details) to the UI. Instead, tracebacks are logged to `stderr` and a generic `_FETCH_ERROR_MSG` constant is emitted to the user. Additionally, `_fetch_one()` in `TipFetcher` now guards the analyst mean price target with `math.isfinite(mean) and mean > 0`, rejecting NaN/inf/non-positive values that could appear as `"nan"` in the UI.
- Code review (`/code-review` at high effort) run on the full diff before commit — returned clean with no correctness bugs.
- All changes committed as `54a62c6` and pushed to `origin/main`.

### Files Changed

- `src/financeguru/db.py` — Added `_CORE_TABLES`, `_CSV_FORMULA_PREFIXES`, `_csv_safe()`; hardened `backup_database()` (pre-chmod), `restore_database()` (schema validation, pre-restore .bak, `init_db()` call), `export_all_csv()` (identifier validation, `_csv_safe()` on all rows, per-file chmod); added `from datetime import datetime` import. (+82 / -4 lines)
- `src/financeguru/prices.py` — Swapped raw `str(exc)` for `_FETCH_ERROR_MSG` constant in both fetcher error paths; log tracebacks to stderr via `traceback.print_exc`; added `math.isfinite` + sign guard on analyst price target. Added `import sys`, `import traceback`. (+20 / -8 lines)

### Commits This Session

- `54a62c6` — harden(security): fix CSV injection, restore safety, file perms

### Decisions Made

- **`_csv_safe()` uses apostrophe prefix** — The OWASP-recommended approach; the apostrophe is stripped by spreadsheet applications before display, so the user sees the original value while formula execution is blocked. Applies to all exported cell values regardless of table.
- **Reject-before-overwrite in restore** — Checking for core tables (not merely probing that the file opens as SQLite) prevents a subtle attack/mistake vector where any SQLite file could wipe the live database. The error message names the missing tables to aid legitimate debugging.
- **Timestamped `.bak` on restore** — The current database is preserved as a recoverable artifact immediately before overwrite. The timestamp in the filename makes successive restores non-colliding.
- **`init_db()` after restore** — Older-schema backups are migrated in place rather than leaving the live session with a schema the running code doesn't expect. Idempotent — existing columns are unaffected.
- **Generic fetch-error message** — URLs, hostnames, and proxy configuration are considered sensitive environment data. Raw exceptions expose these to the user unnecessarily; logging to stderr preserves debuggability without leaking to the GUI.
- **Finiteness + sign guard on analyst target** — `yfinance` can return NaN for mean price targets when analyst coverage is sparse. Filtering at the parse boundary keeps `None` as the canonical "not available" sentinel and prevents downstream display of `"nan"`.

### Issues Encountered

- None. All fixes applied cleanly; code review found no regressions.

### Remaining / Next Session

Intentionally deferred (documented but not changed this session):
- **Leaked daemon threads on fetch timeout** — `prices.py` uses daemon threads for per-ticker timeout; if the outer QThread is torn down while a daemon thread is still in a blocking yfinance call, the thread leaks until process exit. Fix requires injecting a `requests.Session` with native socket timeouts into yfinance so the network call itself is bounded.
- **Loose `pyproject.toml` version ranges** — `PySide6 >=6.7,<7` and `yfinance >=1.3,<2` are fine under Nix (locked by `flake.lock`) but could allow a breaking minor update for `pip install` users.
- **yfinance is an unofficial Yahoo Finance scraper** — Largest residual supply-chain exposure: no SLA, can break on Yahoo API changes, no audit trail. No alternative without a paid market-data API.

Other ongoing items:
- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input (top priority).
- Write pytest tests for the repository layer using an in-memory SQLite database.
- Add user-visible error feedback when yfinance fetch fails (now partially done — generic message is shown; structured retry/rate-limit handling is still open).
- Consider a reporting/charts tab.

---

## Session: 2026-06-07 (Night) — File Menu: Backup, Restore, and Export to CSV

**Duration Estimate**: Single focused session
**Session Focus**: Add a File menu to the main window giving users portable, WAL-safe tools to back up, restore, and export their financial data without touching the file system manually.

### What Was Accomplished

- Added three helpers to `db.py`:
  - `backup_database(dest)` — uses SQLite's online backup API so the copy is transactionally consistent even when a WAL sidecar holds uncommitted pages. Sets `chmod 600` on the output file.
  - `restore_database(src)` — validates the source file is a real SQLite database (executes a probe query before overwriting), then replaces `finance.db` and removes any stale `-wal`/`-shm`/`-journal` sidecars that would otherwise corrupt the freshly restored file. Sets `chmod 600` on the restored file.
  - `export_all_csv(dest_dir)` — queries `sqlite_master` to enumerate all user tables (excluding internal `sqlite_*` entries), exports each to one `<table>.csv` file in the chosen directory, returns the list of written paths. Added `import csv` and `import shutil`.
- Added a `_build_menus()` method to `MainWindow` that creates a `&File` menu with:
  - **Backup Database...** — opens a Save File dialog defaulting to `~/financeguru-backup-YYYYMMDD.db`; calls `db.backup_database`; shows success or error dialog.
  - **Restore Database...** — warns the user with a Yes/Cancel confirmation before proceeding; opens an Open File dialog; calls `db.restore_database`; calls `_refresh_all()` to reload all open tabs; shows success or error dialog.
  - **Export to CSV...** — opens a directory picker; calls `db.export_all_csv`; reports the count and names of files written.
  - **Quit** — bound to `QKeySequence.StandardKey.Quit` (Ctrl+Q on Linux).
- Added `_refresh_all()` to `MainWindow` — iterates all tab widgets and calls `refresh()` on any that implement it. Used after a database restore to guarantee the UI reflects the newly loaded data.
- Added imports to `main_window.py`: `datetime`, `QAction`, `QKeySequence`, `QFileDialog`, `QMessageBox`, and the `db` module.
- Both files compile cleanly; feature confirmed working by the user.

### Files Changed

- `src/financeguru/db.py` — Added `backup_database`, `restore_database`, `export_all_csv`; added `import csv` and `import shutil`
- `src/financeguru/views/main_window.py` — Added `_build_menus()`, `_backup_database()`, `_restore_database()`, `_export_csv()`, `_refresh_all()`; added `datetime`, `QAction`, `QKeySequence`, `QFileDialog`, `QMessageBox`, `db` imports

### Commits This Session

- `cfc597b` — feat(db,ui): add File menu with Backup, Restore, and Export to CSV

### Decisions Made

- **SQLite online backup API instead of `shutil.copy`** — The online API snapshots the database transactionally, merging any pending WAL pages into the destination copy; a raw file copy would capture only the main file and miss WAL data, producing a potentially inconsistent backup.
- **Probe-before-overwrite in `restore_database`** — Executing `SELECT count(*) FROM sqlite_master` on the candidate file confirms it is a valid SQLite database before the live `finance.db` is touched. Prevents corrupting the live database with a non-DB file chosen by mistake.
- **Sidecar cleanup on restore** — After copying, any `-wal`/`-shm`/`-journal` files left from the previous session are removed. Without this step, SQLite would apply the old WAL on top of the restored data and corrupt it.
- **`_refresh_all()` iterates by duck-typing** — Rather than maintaining a registry of views, the helper calls `refresh()` on any tab widget that has the method. This is consistent with how the app already handles tab refreshes elsewhere and requires no changes when future tabs are added.
- **Backup filename default includes date** — `financeguru-backup-YYYYMMDD.db` gives users a sensible default without forcing them to type a name; they can override it freely in the dialog.

### Issues Encountered

- None. Both files compiled cleanly and the feature was confirmed working.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`, `goals`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, bill, and goals data now available.

---

## Session: 2026-06-07 (Evening) — Goals Budgeting Tab

**Duration Estimate**: Single focused session
**Session Focus**: Add a Goals tab that lets users plan and track savings toward a future purchase, automatically wiring each goal to a recurring Bill so monthly contributions show up in the budget.

### What Was Accomplished

- Added a new **Goals** tab positioned immediately after the Debt Snowball tab (eighth tab total).
- Each goal stores a name, price, target month, and optional notes. The "Afford By" date picker shows only month + year and snaps the stored date to the last day of that month, so every goal is fully funded by month-end.
- Monthly savings calculation: `price / months_remaining`, rounded up to the cent via `ROUND_UP`; months floored at 1 so a goal due this month (or already past) never produces a divide-by-zero.
- Adding a goal auto-creates a recurring monthly "Goal" bill in the Bills tab with `amount = monthly_savings`, `due_day = target_date.day`, and `notes = "Goal"`. Editing a goal updates its linked bill. Deleting a goal (with a confirm dialog) also deletes its linked bill.
- Added an **Amount Left** column (right of Price) computed as `price − sum of payments against the goal's bill`, floored at $0. Marking the linked Goal bill as paid in the Bills tab reduces Amount Left on the next Goals tab refresh.
- Added `payment_repo.total_paid_by_bill()` — a single grouped-sum query (`SUM(amount) GROUP BY bill_id`) returning a `dict[int, Decimal]`; used by the Goals tab to compute Amount Left without N+1 queries.
- Added a public `BillsView.refresh()` method so `GoalsView` can trigger a Bills tab refresh after auto-creating or deleting a Goal bill.
- `GoalDialog` shows a live "Save monthly" label that updates on every price or date change — users see the monthly commitment before committing.
- Right-click context menu wired into the Goals table via the existing `attach_row_menu` helper (Add/Edit/Delete).

### Files Changed

- `src/financeguru/models/goal.py` — New: `Goal` dataclass, `months_remaining()` helper, `monthly_savings()` method (new file)
- `src/financeguru/repositories/goals.py` — New: full CRUD (`get_all`, `add`, `update`, `delete`) (new file)
- `src/financeguru/views/goal_dialog.py` — New: Add/Edit goal form with live monthly-savings label; date picker snaps to end of month (new file)
- `src/financeguru/views/goals_view.py` — New: Goals tab view — table, toolbar buttons, bill sync logic, Amount Left computation (new file)
- `src/financeguru/db.py` — Added `goals` table DDL (`id`, `name`, `price`, `target_date`, `bill_id` FK → `bills.id` ON DELETE SET NULL, `notes`)
- `src/financeguru/views/main_window.py` — Imported `GoalsView`; registered Goals tab after Debt Snowball
- `src/financeguru/views/bills_view.py` — Added public `refresh()` method delegating to existing `_refresh()`
- `src/financeguru/repositories/payments.py` — Added `total_paid_by_bill() -> dict[int, Decimal]`

### Commits This Session

- `91b6e44` — feat(goals): add Goals budgeting tab with linked bills and Amount Left tracking

### Decisions Made

- **Goal always snaps to last day of month** — The picker exposes only month + year; the stored date is always the final calendar day of that month. This ensures the goal is fully funded at the end of the chosen month regardless of how many days are in it.
- **Linked bill carries the savings amount** — Instead of a separate Goals payment log, goal contributions are tracked as ordinary payments against a real bill. This means the Bills and Dashboard tabs automatically show the monthly commitment without any special-casing.
- **`ON DELETE SET NULL` on `goals.bill_id`** — If the linked bill is deleted directly from the Bills tab (rather than via the Goals tab), the goal row survives with `bill_id = NULL` and Amount Left falls back to zero-contributed. Prevents orphan goal rows with dangling FKs.
- **Grouped-sum query in `total_paid_by_bill()`** — One SQL call returns all bill totals at once; `GoalsView._refresh()` does a dict lookup per goal rather than a per-goal query. Keeps the refresh O(1) in DB round-trips regardless of how many goals exist.
- **`months_remaining` logic lives in the model** — `Goal.monthly_savings()` delegates to `months_remaining()` (also in `models/goal.py`), keeping math testable in isolation without importing any view or repository code.

### Issues Encountered

- None. All changes are additive; no existing schema columns were modified.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`, `goals`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, bill, and goals data now available.

---

## Session: 2026-06-07 (PM) — Right-Click Menus, Payments Search, and UX Polish

**Duration Estimate**: ~1 hour (17:16 – 17:43 based on commit timestamps)
**Session Focus**: Round out the app's UX by adding keyboard-alternative context menus to every data table and a live search bar to the Payments tab. Also renamed the Salary tab label to "Income" and fixed the icon missing from installed NixOS packages.

### What Was Accomplished

- Renamed the Salary tab display label from "Salary" to "Income" in `main_window.py`; the underlying `SalaryView` module and class name are unchanged.
- Fixed the app icon missing from installed NixOS packages: `flake.nix` `postInstall` previously only copied the `.desktop` file, so `QIcon.fromTheme("financeguru")` found no icon in the store for installed packages. The hicolor SVG is now installed to the prefix, making the icon work both in `nix develop` and on machines using the installed package.
- Created `src/financeguru/views/context_menu.py` — a reusable `attach_row_menu(table, actions)` helper. Right-clicking selects the row under the cursor first; actions with `needs_selection=True` are disabled when nothing is selected; `None` entries in the action list render as separators.
- Wired `attach_row_menu` into all six data tables: Bills, Payments, Income (SalaryView), Stocks, Stock Tips, and Debt Snowball. Each menu mirrors the tab's toolbar buttons and reuses the same handlers — no duplicate logic.
- Added a live search bar to the Payments toolbar (to the right of the existing controls, right-aligned via a stretch spacer). The filter is applied client-side in `_refresh()`: case-insensitive substring match across bill name, displayed amount string, date, and notes. The `QLineEdit.textChanged` signal re-runs `_refresh` on every keystroke. A clear button (`setClearButtonEnabled(True)`) lets the user reset the filter instantly.

### Files Changed

- `src/financeguru/views/main_window.py` — Tab label changed from `"Salary"` to `"Income"`
- `flake.nix` — `postInstall` extended to also install the hicolor SVG icon to the store output
- `src/financeguru/views/context_menu.py` — New module: `ActionSpec` type alias and `attach_row_menu` helper (new file)
- `src/financeguru/views/bills_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Mark Paid actions
- `src/financeguru/views/payments_view.py` — `attach_row_menu` wired in; search `QLineEdit` added to toolbar; `_refresh` updated to apply search filter after the month filter
- `src/financeguru/views/salary_view.py` — `attach_row_menu` wired in with Add/Edit/Delete actions
- `src/financeguru/views/stocks_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Refresh actions
- `src/financeguru/views/stock_tips_view.py` — `attach_row_menu` wired in with Add/Edit/Delete/Refresh Analyst Data actions
- `src/financeguru/views/debt_snowball_view.py` — `attach_row_menu` wired in with Add/Edit/Delete actions

### Commits This Session

- `db3e9c3` — feat(ui): rename Salary tab label to "Income"
- `7aa05cd` — fix(packaging): install app icon into store output
- `cbebb80` — feat(ui): add right-click context menus to all data tables
- `afe95d2` — feat(payments): add search bar filtering bills, amounts, dates, notes
- `108db6c` — style(payments): right-align the search bar in the toolbar

### Decisions Made

- **Reusable helper over per-view duplication** — `attach_row_menu` takes a generic `list[ActionSpec | None]`; every view passes its own callbacks. Adding menus to six tables required zero repeated logic.
- **Client-side search filter** — Applied in Python after `get_all()`, chained with the existing month filter. The payments dataset is small enough that this is never a bottleneck, and it avoids complicating the repository interface.
- **Match on displayed strings, not raw values** — The search checks the `Amount` column's display text (e.g., `"$42.00"`) rather than the raw `Decimal`, so users can search by what they see in the table.
- **`QLineEdit` right-aligned** — Stretch spacer before the search widget mirrors a standard browser/finder search bar placement and keeps the action buttons visually grouped on the left.

### Issues Encountered

- None. All changes are additive; no schema or model changes required.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

