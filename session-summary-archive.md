## Session: 2026-06-16 — Expense Tracking Layer + Spending Charts Tab

**Focus**: Ship the top roadmap item — a reporting/charts tab — starting with spending-over-time.

### What changed (and why)
- Scoped the work end-to-end first (`/interview` → brief at `docs/charts-tab-brief.md`, second-AI reviewed). The interview turned "a charts tab" into two pieces: an arbitrary-expense layer + the charts that read it.
- **Data layer**: new `categories.py` (fixed category list + `GOAL_NOTE`/`SAVINGS_CATEGORY`, single source of truth), `category` column on `bills` (+ migration) and a new `expenses` table, `Expense` model + repo, and `reporting.py` with `monthly_spending(window=12)` / `category_breakdown(year, month)`.
- **UI**: Expenses tab (CRUD), category combobox on the bill dialog, and a Charts tab (QtCharts — stacked by-category bars over 12 months + a per-month breakdown pie). Wired both into `main_window` (8 → 10 tabs).
- Built the data layer + its tests myself (the spending math is the load-bearing part), then fanned the UI/test work out to 3 parallel sub-agents against fixed interface contracts.
- Mid-session the user asked to drop the Total↔By-category toggle — the over-time chart is now always stacked by category.

### Decisions
- Spending universe = **all payments + all expenses** (goal contributions are already payments — categorize a `notes='Goal'` payment as Savings, don't add a third addend = no double-count).
- **Savings excluded from the monthly total** but shown in the breakdown (saving isn't spending). User decision.
- Category = plain `TEXT` column + Python constant, no categories table/management UI (v1). `expenses` added to `_CORE_TABLES` (pre-feature backups now rejected on restore — accepted).
- `reporting.py` is standalone (cross-cuts payments+expenses+bills); sums in `Decimal`, floats only at the QtCharts boundary.

### Issues / surprises
- The reviewer caught that the "Goal" bill is **not** hidden — it's an ordinary bill tagged `notes='Goal'` — which corrected the spending-universe framing before any code was written.
- QtCharts imports cleanly in `nix develop` — no flake change needed.

### Next session
- Net-worth trend view (the deferred charts phase).
- GUI eyeball of the new tabs; decide whether the stacked chart should also exclude Savings.

**Commits**: `714adcd` (feature) + this session-close

---

## Session: 2026-06-15 (pm) — Eliminate prices.py Daemon-Thread Leak

**Focus**: Close roadmap item #1 — the leaked daemon threads in `prices.py`.

### What changed (and why)
- Removed `_call_with_timeout` (and the `threading` import) — the daemon-thread-per-fetch wrapper *was* the leak: after its 15s join expired the orphaned thread kept running while yfinance's own request finished. Replaced with a direct `_safe_call(fn) -> (ok, value)`.
- Added `_make_session()`: a `curl_cffi` session that preserves yfinance's Chrome impersonation but subclasses `request()` to cap every request's socket timeout at 8s. Both fetchers now pass `session=` into `yf.Ticker(...)`, verified to reach yfinance's request layer.
- `TipFetcher._fetch_one` now returns `(failed, data)` so a capped-timeout/network error marks the ticker failed (via the existing `partial_error` signal), while a ticker with genuinely no analyst coverage is not flagged.
- Rewrote `test_prices.py` to cover `_safe_call` and the session timeout cap. Suite 69 → 71, all green. Live smoke test: AAPL $296.42 in 1.4s, bogus ticker reported failed, MSFT tip returned real data — all through the capped session.

### Decisions
- **Approach: eliminate the thread layer, not just bound it.** The leak premise was outdated — yfinance 1.3.0 already has native timeouts + retries + 429 handling. So rather than keep `_call_with_timeout` as a belt-and-suspenders, dropped it entirely and lean on the native socket timeout. Cleaner and removes the whole nested-daemon-thread class.
- **Keep curl_cffi, don't inject a plain `requests.Session`.** The roadmap note predates yfinance's curl_cffi move; a plain session would drop Chrome impersonation and invite Yahoo blocking. Subclassed the curl_cffi session instead.
- **Cap in `request()`, not via session default.** yfinance passes `timeout=30` explicitly on every call, overriding any session-level default — clamping inside `request()` is the only effective lever.

### Issues / surprises
- Roadmap item #2 (retry / rate-limit backoff) is now **largely redundant** — yfinance 1.3.0 provides retry/backoff (`YfConfig.network.retries`) and `YFRateLimitError` on 429 out of the box. Flagged in project-state.md and saved to memory.

### Next session
- Reporting/charts tab (spending over time, net-worth trend) — now the top new-feature item.
- (Optional) offscreen-Qt harness so the views can be smoke-tested.

**Commits**: `96bb9c9` (1 commit) + this session-close

---

# Session Summary — Archive

_Active log: [session-summary.md](session-summary.md). Older entries are appended here on rotation, most recent first._

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

## Session: 2026-06-07 — Payments Edit Button and Current-Month Filter

**Duration Estimate**: Short follow-on session (same calendar day as previous session)
**Session Focus**: Round out the Payments tab to match the Bills tab's UX — add in-place editing of existing payment records and a quick toggle to filter the list down to the current month.

### What Was Accomplished

- Added `payment_repo.update()` — executes an `UPDATE payments SET ... WHERE id=?` using all mutable fields (`bill_id`, `amount`, `paid_date`, `notes`).
- Extended `PaymentDialog` to support editing an existing payment: accepts an optional `payment: dict` argument, switches the window title to "Edit Payment", stores the incoming `id` on `self._payment_id`, and pre-fills the bill combo, amount spinbox, date picker, and notes field via a new `_prefill()` method. The returned `Payment` dataclass now carries the original `id` so `payment_repo.update()` can target the correct row.
- Added an **Edit** button to the Payments toolbar (between Add and Delete), enabled/disabled in sync with the Delete button via `_on_selection_changed`. Clicking Edit opens a pre-filled `PaymentDialog`; accepting calls `payment_repo.update()` and refreshes the table.
- Wired **double-click-to-edit**: `QTableWidget.doubleClicked` connects to the same `_on_edit` handler so power users can bypass the button.
- Added a **"This month only"** `QCheckBox` to the right of the Delete button, checked by default. When checked, `_refresh()` filters `payment_repo.get_all()` to rows whose `paid_date` starts with the current `YYYY-MM-` prefix. Unchecking shows the full history. The checkbox state is wired via `toggled` → `_refresh`.

### Files Changed

- `src/financeguru/repositories/payments.py` — Added `update(payment: Payment) -> None`
- `src/financeguru/views/payment_dialog.py` — Optional `payment: dict` constructor arg; `_payment_id` field; `_prefill()` method; `id` included in returned `Payment`
- `src/financeguru/views/payments_view.py` — Added `Edit` button, `"This month only"` checkbox, `_on_edit()` handler, double-click-to-edit signal, updated `_on_selection_changed` to gate both buttons, client-side month filter in `_refresh()`

### Commits This Session

- _(staged, not yet committed — will be captured in the session-close commit)_

### Decisions Made

- **Client-side month filter** — The filter is applied in Python after `get_all()` rather than as a SQL `WHERE` clause, keeping the repository interface simple. The full dataset is small enough that this is never a bottleneck.
- **`payment: dict` rather than `Payment` dataclass** — `PaymentDialog` already received `sqlite3.Row` / dict-like objects from `_rows`; passing that directly avoids an extra conversion step and keeps the pre-fill code consistent with how the Bills dialog was already structured.
- **Edit button mirrors Bills tab pattern exactly** — Add, Edit, Delete left-aligned; stretch spacer after; enabled/disabled by selection. Consistency across tabs reduces cognitive overhead.

### Issues Encountered

- None. Changes are straightforward additions with no schema changes required.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-07 — Currency Precision (Decimal) and Security Hardening

**Duration Estimate**: ~30 minutes (09:42 – 10:11 based on commit timestamps)
**Session Focus**: Eliminate IEEE-754 float error from all monetary arithmetic and close out a full security audit covering DB permissions, input validation, dependency pinning, and network-call safety.

### What Was Accomplished

- Introduced `money.py` with helpers (`to_decimal`, `optional_decimal`, `cents`, `ZERO`, `CENT`) and registered a `sqlite3` adapter so `Decimal` values bind transparently to `REAL` columns — existing databases load unchanged.
- Migrated all currency, rate, and share fields in every model, repository, view, and simulation to `Decimal`. Float-to-Decimal coercion happens at the read boundary (repository layer); views convert back to `float` only for Qt spinboxes.
- Rewrote `snowball.py` to simulate entirely in `Decimal`, quantizing to cents only at the output boundary — eliminates error accumulation in up to 600-month simulations.
- Rewrote `budget.py` monthly normalization to use exact `Decimal` division from integer ratios instead of pre-rounded float factors.
- Locked down `finance.db` file permissions: data directory set to `0700`, database file set to `0600`, so plaintext financial data is not world-readable on multi-user machines.
- Added `prices.py` price validation: coerces `last_price` to a finite, positive value or `None` — prevents `nan`/`inf`/`None` from rendering as "nan" in market value and gain/loss columns.
- Added per-ticker 15-second timeout to every yfinance call (daemon thread + `join`) in both `PriceFetcher` and `TipFetcher`; re-enabled the Refresh button via the thread's `finished` signal; added `quit()`/`wait()` shutdown in `closeEvent`.
- Added `validators.py` with `normalize_ticker()` — restricts user-supplied tickers to letters, digits, `.`, `-` (max 12 chars) before they reach yfinance or the DB.
- Wired `normalize_ticker()` into `StockDialog` and `StockTipDialog` on both the Accept and Fetch paths.
- Added identifier validation to `db.py:_ensure_column` (table/column name allowlist + DDL prefix check) to close a latent injection sink.
- Added `ON DELETE CASCADE` to the `payments.bill_id` FK in the `init_db` schema for new databases; the repository-level explicit child delete is retained for backward compatibility with existing databases.
- Pinned `PySide6 (>=6.7,<7)` and `yfinance (>=1.3,<2)` in `pyproject.toml` so non-Nix pip installs cannot silently pull a regressed or malicious release.
- Added `*.db` / `*.sqlite*` patterns to `.gitignore` so the financial database can never be committed accidentally.

### Files Changed

- `src/financeguru/money.py` — New module: `Decimal` helpers and `sqlite3` adapter registration (new)
- `src/financeguru/db.py` — Decimal adapter; `0700`/`0600` fs permissions; `_ensure_column` identifier validation; FK cascade on `payments.bill_id`
- `src/financeguru/models/bill.py` — Currency fields changed to `Decimal`
- `src/financeguru/models/debt.py` — Balance, APR, and payment fields changed to `Decimal`
- `src/financeguru/models/income.py` — Amount field changed to `Decimal`
- `src/financeguru/models/payment.py` — Amount field changed to `Decimal`
- `src/financeguru/models/stock.py` — Price and share fields changed to `Decimal`
- `src/financeguru/models/stock_tip.py` — Price fields changed to `Decimal`
- `src/financeguru/repositories/bills.py` — Coerce money fields via `to_decimal` at read boundary; `ON DELETE CASCADE` note
- `src/financeguru/repositories/debts.py` — Coerce all numeric fields via `to_decimal`/`optional_decimal`
- `src/financeguru/repositories/incomes.py` — Coerce amount via `to_decimal`
- `src/financeguru/repositories/payments.py` — Coerce amount via `to_decimal`
- `src/financeguru/repositories/stock_tips.py` — Coerce price fields via `optional_decimal`
- `src/financeguru/repositories/stocks.py` — Coerce price/share fields via `to_decimal`/`optional_decimal`
- `src/financeguru/snowball.py` — Full simulation in `Decimal`; cent-quantize at output boundary
- `src/financeguru/budget.py` — Monthly normalization via exact `Decimal` division
- `src/financeguru/prices.py` — Price validation (finite, positive, or `None`); 15s per-ticker timeout in `PriceFetcher` and `TipFetcher`
- `src/financeguru/validators.py` — New `normalize_ticker()` function (new)
- `src/financeguru/views/bill_dialog.py` — Read `Decimal` via `float()` for spinboxes; build models with `cents()`
- `src/financeguru/views/dashboard_view.py` — Decimal-aware display
- `src/financeguru/views/debt_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/income_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/payment_dialog.py` — Spinbox read/write via `float()`/`cents()`
- `src/financeguru/views/stock_dialog.py` — Ticker normalized via `normalize_ticker()`; fetched price coerced to `Decimal`
- `src/financeguru/views/stock_tip_dialog.py` — Ticker normalized via `normalize_ticker()`
- `src/financeguru/views/stocks_view.py` — Re-enable Refresh button on `finished`; `quit()`/`wait()` on `closeEvent`
- `src/financeguru/views/stock_tips_view.py` — Re-enable Refresh button on `finished`; `quit()`/`wait()` on `closeEvent`
- `pyproject.toml` — Pinned `PySide6 >=6.7,<7` and `yfinance >=1.3,<2`
- `.gitignore` — Added `*.db` / `*.sqlite*`

### Commits This Session

- `dd62198` — fix(security): lock down DB perms, validate prices, bound fetch timeouts
- `c4a0cec` — harden(security): pin deps, validate tickers, guard DDL, FK cascade
- `38996f8` — refactor(money): represent currency as Decimal, not float

### Decisions Made

- **`Decimal` stored as `REAL`, not `TEXT`** — Avoids a schema migration; cent-quantized values round-trip through SQLite `REAL` exactly because they fit in the 53-bit mantissa. The `sqlite3` adapter handles binding transparently.
- **Coerce at the read boundary, not the write boundary** — Repositories convert incoming `sqlite3.Row` values to `Decimal` once; all internal logic then operates on exact types without defensive casting at every call site.
- **Backward-compatible FK cascade** — New databases get `ON DELETE CASCADE` on `payments.bill_id`; the explicit child-delete in `bills.delete()` is kept so existing databases (created before this change) still clean up correctly.
- **15-second per-ticker timeout via daemon thread** — The simplest portable approach for yfinance, which does not expose a native timeout parameter; the daemon thread exits automatically on process termination if the join timeout expires.

### Issues Encountered

- None blocking. All changes verified with Decimal unit tests, an offscreen GUI smoke test, and a live-DB load pass.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages` (top priority).
- Write pytest tests for the repository layer (`bills`, `payments`, `stocks`, `debts`, `incomes`, `stock_tips`) using an in-memory SQLite database.
- Add user-visible error feedback when yfinance price or analyst data fetch fails (network error, rate limit).
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

---

## Session: 2026-06-05 — Stock Tips, Debt Snowball, Salary, and Lump-Sum Payments

**Duration Estimate**: ~4 hours (17:36 – 21:27 based on commit timestamps)
**Session Focus**: Expand the app from four tabs to seven by implementing Stock Tips, Debt Snowball with full payment simulation, and a Salary/budget visualizer — all fully wired into the existing SQLite schema.

### What Was Accomplished

- Implemented the Stock Tips tab: track personal tips (ticker, action, target price, confidence, notes) stored in a new `stock_tips` table; a Refresh Analyst Data button fetches yfinance analyst consensus and mean price target, caching them in the DB without overwriting user-entered values.
- Implemented the Debt Snowball tab: CRUD for debts (balance, APR, minimum payment); a pure-Python month-by-month simulator (`snowball.py`) computes both Snowball and Avalanche strategies with rolling extra payments; a side-by-side summary shows total interest paid and months saved per strategy.
- Added a detailed per-debt monthly payment schedule table to the Debt Snowball tab: shows exactly how much goes to minimum vs. rolling-extra payments for each debt each month; strategy-selectable.
- Added one-time lump-sum extra payments to the Debt Snowball calculator: model windfalls (tax refund, bonus) tied to a specific month; lump amount rolls onto the highest-priority debt first, cascading any leftover to the next debt; surfaced in both the summary and the schedule table.
- Implemented the Salary tab: income CRUD with paycheck frequency (weekly / biweekly / semimonthly / monthly / annual); normalizes all incomes to a monthly figure; subtracts monthly bills to show surplus spending money; a savings-rate slider splits surplus into a proportional save-vs-spend bar with monthly and annual projections.
- Added "specific days" pay frequency to the Salary tab: for paychecks tied to calendar dates (e.g., 1st and 15th); a day-picker grid (1–31) appears in the dialog; monthly income = per-paycheck amount × count of selected days; stored as comma-separated string in a new `pay_days` column with idempotent migration.
- All tabs now refresh on selection via `currentChanged` so cross-tab figures (bills total, income surplus) stay current.

### Files Changed

- `src/financeguru/db.py` — Added `stock_tips`, `debts`, and `incomes` table DDL; added `pay_days` column with try/except migration guard
- `src/financeguru/models/stock_tip.py` — `StockTip` dataclass (new)
- `src/financeguru/models/debt.py` — `Debt` dataclass (new)
- `src/financeguru/models/income.py` — `Income` dataclass with `pay_days` field
- `src/financeguru/repositories/stock_tips.py` — Full CRUD + analyst data update (new)
- `src/financeguru/repositories/debts.py` — Full CRUD for debts (new)
- `src/financeguru/repositories/incomes.py` — Full CRUD for incomes with `pay_days` support
- `src/financeguru/prices.py` — Extended with `AnalystFetcher` QThread for analyst consensus data
- `src/financeguru/snowball.py` — Pure-Python Snowball/Avalanche simulator with lump-sum support and monthly payment schedule recording (new)
- `src/financeguru/budget.py` — Shared frequency-to-monthly normalization, including specific-days logic
- `src/financeguru/views/main_window.py` — Wired Stock Tips, Debt Snowball, and Salary tabs; hooked `currentChanged` for all tab refresh
- `src/financeguru/views/stock_tip_dialog.py` — Add/Edit stock tip form (new)
- `src/financeguru/views/stock_tips_view.py` — Stock Tips tab view with Refresh Analyst Data (new)
- `src/financeguru/views/debt_dialog.py` — Add/Edit debt form (new)
- `src/financeguru/views/debt_snowball_view.py` — Debt Snowball tab with summary, schedule table, and lump-sum entry (new)
- `src/financeguru/views/income_dialog.py` — Add/Edit income form with specific-days day-picker grid
- `src/financeguru/views/salary_view.py` — Salary tab with budget visualizer and savings-rate slider

### Commits This Session

- `25f37bd` — feat: add Stock Tips tab with analyst data from yfinance
- `6b06eb8` — feat: add Debt Snowball tab with Snowball vs Avalanche comparison
- `1d661c1` — feat: add payment schedule table to Debt Snowball tab
- `16ef976` — feat: add one-time lump-sum payments to Debt Snowball calculator
- `401e9f7` — feat: add Salary tab with budget and savings visualizer
- `77f3027` — feat: add "specific days" pay frequency for exact paydays

### Decisions Made

- **Pure-Python snowball simulator** — No external dependencies; a single-pass month-by-month loop handles both strategies, rolling extra payments, and lump-sum windfalls. Keeps the logic testable and portable.
- **`budget.py` shared normalization layer** — Frequency-to-monthly math lives in one module consumed by the Salary view and income repository, avoiding duplication.
- **Specific-days stored as comma-separated string** — Simple to query and display; monthly income is amount × count of days, treating each calendar date as one paycheck per month.
- **Analyst data cached in DB** — yfinance data is written to `stock_tips` columns on refresh but never overwrites user-entered values; avoids repeated network calls on every view load.
- **Idempotent column migrations** — New columns added with `ALTER TABLE ... ADD COLUMN` inside a try/except so existing DBs silently receive the new column without requiring a manual migration step.

### Issues Encountered

- None blocking. The specific-days monthly calculation requires a deliberate modeling decision (count of selected days = paychecks per month); documented in project-state.md.

### Remaining / Next Session

- Wire `financeguru` into `~/NixOS/flake.nix` as a flake input and add to a host's `environment.systemPackages`.
- Write pytest tests for the repository layer (bills, payments, stocks, debts, incomes, stock_tips) using an in-memory SQLite DB.
- Add user-visible error feedback when yfinance price or analyst data fetch fails.
- Consider a reporting/charts tab using the salary, debt, and bill data now available.

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
