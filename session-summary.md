# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

## Session: 2026-07-07 — Packaged-App Qt Fix + `/improve-system` Sweep

**Focus**: Fix the *installed* FinanceGuru package failing to launch on natalie-laptop (`no Qt platform plugin could be initialized`), then run a full `/improve-system` maintenance sweep.

### What changed (and why)
- **Fixed `packages.${system}.default` in `flake.nix`** — the 2026-07-04 devShell fix never touched the actual packaged app. Root cause: `wrapQtAppsHook`'s automatic wrap pass runs *before* `buildPythonApplication`'s own Python wrap, so the Qt env vars it sets (`QT_PLUGIN_PATH` included) were silently dropped from the final wrapper — `nix build` succeeded with no error while the app was still fundamentally broken. `libxcb-cursor.so` was also still missing from the closure. Fix: `dontWrapQtApps = true` + an explicit `postFixup` re-wrap after the Python wrap, so the Qt args land last.
- **Verified by inspecting the built wrapper directly** (`strings` on `bin/financeguru` inside `nix develop`) and actually running the binary live on this machine's Wayland session, not just trusting `nix build`'s exit code.
- **New skill: `qt-nix-wrapper-diagnose`** — captures this diagnostic technique; `wrapQtAppsHook` issues showed up in 11 of ~20 past FinanceGuru sessions per transcript grep, so this is a real recurring pain point, not a one-off.
- **`/improve-system` full 5-skill sweep**: added a Gotcha to the `interview` skill (NixOS repo) about scaling the ceremony down for well-scoped technical fixes; skill-audit (3 parallel sub-agents) found zero correctness bugs across all 5 project-local skills — `new-feature` now delegates commits to `git-commit`, `db-migration`/`qt-smoke` had duplicated code templates extracted to `assets/`, `audit`'s `## Modes` renamed to `## Arguments`; claude-rules and fewer-permission-prompts both came back clean.

### Decisions
- Scoped via a deliberately lightweight `/interview` (two `AskUserQuestion` prompts, not the full Project Brief + second-AI-review ceremony) since this was a single, already-diagnosed bug — captured as a Gotcha so future sessions know when this is appropriate.
- Held all four skill-audit refactors for explicit user confirmation before applying (per `/improve-system`'s structural-change gate), then implemented all four once approved.

### Issues / surprises
- The bug was invisible to `nix build`/`nix flake check` entirely — both passed the whole time the packaged app was broken. Static build success doesn't prove a Nix-wrapped app's runtime env is correct; only inspecting the wrapper and running it does.

### Next session
- **Priority**: bump the `financeguru` input in the NixOS repo and rebuild natalie-laptop — it cannot launch the app at all until it picks up this fix.
- Check CI went green on GitHub Actions; build the net-worth trend chart; GUI-eyeball the Charts/Expenses tabs.

**Commits**: `517d45e..839ce63` (2 commits, FinanceGuru) + `470963e` (1 commit, NixOS repo — interview skill gotcha)

---

## Session: 2026-07-04 — devShell Qt Crash Fix + `/improve-system` Maintenance

**Focus**: Fix `python -m financeguru.main` aborting at startup in `nix develop`, then run a full `/improve-system` maintenance sweep.

### What changed (and why)
- **Fixed the devShell Qt platform plugin crash** (`flake.nix`): `LD_LIBRARY_PATH` now includes `pkgs.libxcb-cursor` (the xcb plugin dlopens `libxcb-cursor.so` at runtime), and `QT_PLUGIN_PATH` is pinned to `pkgs.qt6.qtbase`'s own plugin dir instead of inheriting the KDE Plasma login shell's value, which pointed at a different, ABI-incompatible qtbase build.
- **`/improve-system` full sweep**: added `Bash(nix develop *)`, `Bash(nix eval *)`, `Bash(nix flake check)`, `mcp__nixos__nix` to `.claude/settings.json`'s allowlist (usage-ranked from recent transcripts); confirmed all 4 project-local skills, all 4 CLAUDE.md standing rules, and no misfiring skills — everything else came back clean.

### Decisions
- Root-caused with `coredumpctl` + `gdb` rather than guessing — the backtrace (`QApplicationPrivate::init()` → `qFatal`) plus `ldd`/`QT_PLUGIN_PATH` inspection pinned the exact ABI mismatch (system `qtbase-6.11.1` vs. project `qtbase-6.11.0`).
- Left the remaining `union.general` KDE-theme-plugin and Wayland icon-pixmap console warnings alone — confirmed cosmetic (even `dolphin` hits variants of this) and not a regression from the fix.

### Issues / surprises
- The Bash tool's own sandbox couldn't reproduce the crash at all (silent abort, no captured output) until run with `dangerouslyDisableSandbox` — the real display/session access mattered for reproducing a GUI startup crash.

### Next session
- (unrelated to this session) Check CI went green on GitHub Actions; build the net-worth trend chart; bump the `financeguru` input in the NixOS repo.

**Commits**: `2b9efdc..fadd318` (2 commits)

---

## Session: 2026-07-02 — Net-Worth Snapshots, Auto Backups, Smoke Tests, CI, Overdue Bills (closed 2026-07-03)

**Focus**: "What would you improve?" → all five answers shipped as one scoped effort: snapshot data layer, rotating backups, view smoke tests, flake-check CI, and overdue bills that stop vanishing.

### What changed (and why)
- **Daily net-worth snapshots** (`snapshots` table + repo, captured at launch and after a full price refresh, same-day upsert): the trend chart can't be back-filled — stocks store only purchase price — so every week without the table was history lost forever. Data layer ships now; the chart comes once history has accrued.
- **Automatic rotating backups**: `auto_backup()` at launch, deliberately *before* `init_db()` so the copy captures the pre-migration database; skip-if-today's-exists; keep 14; pruning can never touch `.pre-restore-*.bak` safety copies. Protects against the failure mode manual backups never cover.
- **Overdue one-time/yearly bills persist until paid** as "Overdue (Month)" dashboard rows, cycle-scoped paid check (a 2025 payment can't satisfy the 2026 cycle), counted in Total/Remaining. Was silently dropping unpaid bills once their month passed — late-fee territory.
- **View smoke tests** (`test_views_smoke.py` + shared session `QApplication` fixture): MainWindow + every tab constructed offscreen, public `refresh()` contract locked in — the exact contract whose violation was audit #4's only real bug.
- **CI**: `checks.x86_64-linux.{package,pytest}` in the flake (sandboxed offscreen pytest) + a thin GitHub Action running `nix flake check`, so local verification and CI are the same command. 151 tests total (was 113).
- Also in this close range: `98dd868` (2026-06-29, `/improve-system` maintenance — CLAUDE.md sync + pytest permission allowlist).

### Decisions
- Goal savings computed live via `goals.bill_id`; deleted goals drop out of future snapshots, past rows immutable. Accepted: "tracked net worth" (no cash/property), per-machine gap-filled series.
- Launch hooks in `main.py`, not `MainWindow`, so tests constructing the window never write backups/snapshots.
- Reviewer's TEXT-money-column suggestion rejected — project convention is `REAL` + the `Decimal` adapter.

### Issues / surprises
- The session **hit its usage limit** right after implementation — verification, commit, and close all happened next session (2026-07-03). Everything then verified clean: 151 tests, `nix flake check`, and the real launch sequence driven twice against a throwaway `$HOME` (backup rotation, snapshot dedup, 10 tabs offscreen).
- The brief-review agent found 7 genuine ambiguities pre-build (goal-deletion semantics, backup ordering, cycle scoping) — settling them up front meant zero mid-build design stalls.

### Next session
- Check the first real CI run went green on GitHub Actions.
- Net-worth trend chart over the accruing snapshots.
- Bump the `financeguru` input in the NixOS repo + rebuild hosts so the machines start accruing snapshots/backups.

**Commits**: `98dd868..e60442a` (2 commits) + this close

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

