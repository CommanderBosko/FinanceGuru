# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

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
