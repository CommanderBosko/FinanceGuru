# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

## Session: 2026-06-26 — Whole-Codebase Audit (#4) + Fixes

**Focus**: Run a full audit of the clean codebase and fix everything it surfaced.

### What changed (and why)
- **Audit fanned out across four parallel lenses** (data/SQL, network/prices, views/QThread, domain/money), then findings consolidated and all fixed in one commit (`c5d9598`). With a clean tree the diff-based `/security-review` and `/code-review` skills have nothing to review, so the pass leaned on the project risk checklist + the review sub-agents.
- **One real correctness bug**: `MainWindow._refresh_all` duck-types `refresh()`, but `PaymentsView`/`StocksView`/`StockTipsView`/`DebtSnowballView` only had private `_refresh`/`_load`, so a **DB restore reported success while those four tabs kept showing pre-restore data**. Added the public alias to all four.
- **Security/data**: CSV exports now created `0600` up front (no world-readable window) with header cells also `_csv_safe`'d; `get_connection` is a closing `@contextmanager`.
- **Correctness**: snowball pre-marks zero-balance debts so they don't inflate the rolling pool; tighter ticker regex rejects degenerate symbols; analyst-count cells guarded against NaN; unknown income frequency logged to stderr.
- **Quality**: deduped right/center cell builders into `views/_table.py`; chart axes `deleteLater()`'d on rebuild; `StockTipDialog` frees its prior fetcher; `bill_dialog`/`debt_dialog` name validation aligned; models default `category` from `DEFAULT_CATEGORY`; stale `GOAL_NOTE` comment fixed.
- 113 tests still green; offscreen smokes verified the fixes (validators, snowball, CSV perms, refresh hooks, MainWindow build/teardown, dialog validation).

### Decisions
- **Fixed the four views, not the gate** — added public `refresh()` aliases to preserve `_refresh_all`'s duck-typed pattern rather than special-casing it.
- **`get_connection` wrapped, not all callers refactored** — a `@contextmanager` keeps `with conn` transaction semantics and adds deterministic close; all 60 callers already used `with`, so it was transparent.
- **Snowball pre-mark over in-loop guard** — marking zero-balance debts `payoff_month=0` up front fixes both the phantom-payment roll-up and the None-in-sort risk in one place.

### Issues / surprises
- The stale-after-restore bug had been latent and even flagged as a "cautionary example" in past notes (`PaymentsView` has only `_refresh`) — but nobody had connected it to the restore path actually showing wrong data. The audit's verification of the restore flow is what surfaced it.

### Next session
- Net-worth trend view (still the top deferred item).
- Optional: GUI eyeball of Charts/Expenses; decide whether the stacked over-time chart should also exclude Savings.

**Commits**: `c5d9598` (1 commit) + this close

---

## Session: 2026-06-22 — User-Managed Categories, Category Rename Migration, Savings-Calc Expenses, Two Skills

**Focus**: Let the user manage their own spending categories, rename two of them cleanly, and make the savings calculator account for actual spending.

### What changed (and why)
- **Two categories then full feature, staged** (`abc82c3`, `745874c`): added "Eating out"/"Pets" as a one-line list change, then promoted categories from a fixed Python list to a seeded `categories` table with a repo, a "Manage Categories…" dialog (add/rename/delete), and protected Savings/Other. Bill/expense pickers and charts now read the live list from the DB. Each stage was an independent, reviewable commit (user chose "both, staged").
- **Food→Groceries, Eating out→Restaurants** (`b1924d9`): updated the seed list and added a guarded, idempotent `_rename_category` migration in `init_db()` that renames the row **and re-tags** existing bills/expenses, so reports don't show split old/new buckets. Runs before the seeding loop so `INSERT OR IGNORE` doesn't re-add the old name.
- **Savings calculator nets out the month's expenses** (`6b506fe`): the Income tab's Monthly Budget now subtracts `expenses.total_for_month(current)` on top of bills, with a new "This Month's Expenses" line. Expenses table only (not payments — bills already count as obligations).
- **Two project skills** (`9517733`): `db-migration` (the schema-change conventions this session surfaced) and `new-feature` (end-to-end layered build checklist), the latter delegating to `db-migration`/`qt-smoke`/`audit`.
- 100 → 113 tests; each change verified with pytest + a headless `qt-smoke`.

### Decisions
- **Protected categories** (Savings, Other) can't be renamed/deleted — reporting hard-codes those names; guarded in both the UI and the repo SQL.
- **Category columns stay free text** — in-app rename is picker-only by design; the *code* rename migration re-tags records (the complete version). Intentional asymmetry, documented in both places.
- **Migration before seeding**, guarded for idempotency; tested by simulating a pre-rename DB since the conftest fixture only starts fresh.
- Savings calc uses the **current calendar month**, expenses table only — so "Extra" starts high and shrinks as spending is logged (intended for a running calculator).

### Issues / surprises
- The conftest `temp_db` fixture always runs a fresh `init_db()`, so it never exercises the migration's *upgrade* path — the migration tests have to roll the DB back to the old shape first. Captured this as a gotcha in the `db-migration` skill.

### Next session
- Net-worth trend view (still the top deferred item).
- Optional: make the in-app category rename also re-tag records, to match the migration's behavior (raised, not done).

**Commits**: `abc82c3..9517733` (5 commits + this close)

---

## Session: 2026-06-17 — Audit Pass #3, Per-Month Bill Scheduling, Two Skills

**Focus**: Re-audit the grown codebase, fix what it surfaced, and capture the recurring workflows as skills.

### What changed (and why)
- **Audit #3 + fixes** (`a323e87`): the new modules were security-clean, but the QThread teardown was the real bug — views nested in a `QTabWidget` never get `closeEvent`, so the fetcher-cleanup was dead code and could abort the app on quit mid-fetch. Wired `MainWindow.closeEvent → stop_threads()`, added dialog `done()` cleanup, and a cancellable `_TickerFetcher`/`stop_fetcher`. Also scoped the dashboard to bills actually due this month, and made goal→Savings categorization key off the `goals.bill_id` FK instead of the `notes='Goal'` string (collision fix).
- **Per-month bill scheduling** (`6a0c678`, `251ad48`): added nullable `due_month` (yearly) and `due_year` (one-time) columns + `Bill.is_due_in()`, so yearly/one-time bills show on the dashboard in their actual month instead of being dropped or counted every month.
- **Self-audit of the day's own diff** (`8328e36`): found `stop_fetcher`'s bounded wait could be outrun by a multi-request ticker → added an unbounded fallback; stopped per-refresh thread accumulation; hoisted the goal-bill lookup; added QThread signal/cancel/stop tests. 91 → 100 tests.
- **Two project-local skills** (`e63a4f9`): `qt-smoke` (offscreen-Qt view verification — the harness that was a roadmap "optional") and `audit` (comprehensive review orchestrating /security-review + /code-review + the project risk checklist + tests).

### Decisions
- Goal contributions identified by the **goals FK, not note text** — collision-free, NULL-safe, no migration needed (reporting keys off the live FK).
- `Bill.is_due_in()` on the **model**, not the view — pure-Python, unit-testable without Qt.
- `stop_fetcher` falls back to an **unbounded wait** — `cancel()` only lands between tickers and one ticker can issue several 8s-capped requests, so a bounded wait alone could still destroy a live thread.
- **No CLAUDE.md skills catalog** — Claude auto-loads skill name+description each session; a list would be a drift-prone second source of truth (user's call).

### Issues / surprises
- The teardown `closeEvent` overrides on the views had been dead since they were written — Qt only delivers `closeEvent` to top-level windows, not `QTabWidget` children.

### Next session
- Net-worth trend view (deferred charts phase).
- Optional: decide whether past-due one-time bills should keep showing on the dashboard.

**Commits**: `a323e87..e63a4f9` (5 commits + this close)

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

