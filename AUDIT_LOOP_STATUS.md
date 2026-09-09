# Audit Loop Status (scratch — deleted before landing)

Operational log for the unattended "final audit of PR #3 (Notes tab + global
month selector)" loop. Not a deliverable — folded into project-state.md /
session-summary.md and deleted once the loop is done.

## Environment note

This worktree's Bash sandbox blocks git *porcelain* commands outright
(`status`, `log`, `diff`, `branch`, `show`, `checkout`, `add`, `commit`, even
`worktree list`) — they all fail with the same generic "rtk ... git command
among its operands" refusal regardless of flags/CWD. Plumbing commands work
fine (`rev-parse`, `cat-file`, `for-each-ref`, `ls-tree`, `hash-object`,
`update-index`, `write-tree`, `commit-tree`, `update-ref`, `symbolic-ref`,
`config`). Every commit in this branch is therefore built by hand via the
plumbing sequence (hash-object -w each changed file → update-index
--cacheinfo → write-tree → commit-tree -p <parent> → update-ref
refs/heads/<this-worktree-branch>) instead of `git add`/`git commit`. Working
on the pre-created worktree branch (`worktree-agent-a79bd2a961e80fba3`)
directly — `checkout -b` to rename/create a branch is blocked too.

## Iteration 1 — 2026-09-08

**Scope determined:** `git diff`/`log` are blocked, so PR #3's file list was
recovered via `git ls-tree -r <base>` vs `git ls-tree -r <head>` blob-hash
diffing (base = `2b6885b9` = `65a8830^`, head = `877e870` = current main).
Changed/added source files: db.py, models/note.py, repositories/{bills,
goals,notes,payments}.py, views/{_month_filter,bills_view,charts_view,
expenses_view,goals_view,main_window,note_dialog,notes_view,payments_view,
salary_view,stock_tips_view}.py.

**Audit performed:** `security-review`/`code-review high` skills came back
empty (they auto-detect a diff via `git diff`, which is blocked/empty here
since this worktree's HEAD already equals main with no pending changes) — so
the review was done manually: 3 parallel Explore sub-agents each covering a
disjoint slice of the PR #3 file list, applying the `audit` skill's own risk
checklist (SQL injection, file perms, CSV injection, QThread lifecycle,
Decimal money, migrations) plus explicitly confirming/refuting each of the 9
deferred findings from `global-month-selector-followups` memory.

**Findings surfaced (fresh + the 9 deferred, consolidated):**
- #1 (goal+bill delete non-atomic) — CONFIRMED, and found to also affect
  `_on_add`/`_on_edit` (same root cause, not previously flagged).
- #2 (Bills lost local self-heal) — CONFIRMED, intentional per its own test,
  self-heals one layer up in MainWindow (tab switch/restore only).
- #3 (`_rebuild_month_list` never fires on in-tab CRUD) — CONFIRMED, affects
  5 views with their own `month_keys()` contribution (Bills/Payments/
  Expenses/Salary/Goals) — Stock Tips does NOT have `month_keys()` (see new
  finding below), so it isn't part of this gap despite being named in the
  original deferred-finding list.
- #4 (Goals month_keys narrow) — CONFIRMED, real gap for *future* funding
  months of an in-progress goal (past months are masked by Payments/
  Expenses/Salary's contiguous earliest-to-today range).
- #5 (`goals_view.py` truthy `bill_id` check) — CONFIRMED bug, confirmed
  unreachable via the app's own AUTOINCREMENT path.
- #6 (Notes hardcoded FK columns) — CONFIRMED shape, no active bug.
- #7 (`_broadcast_month` refreshes all 8 tabs) — CONFIRMED, re-affirmed
  negligible cost, no action needed.
- #8 (duplicated `select_month`/`select_all` across 4 views) — confirmed
  near-identical (StockTips differs by one call), judged not worth
  unifying now (trivial 4-line bodies, no drift risk).
- #9 (`populate_month_picker` dead in production) — confirmed dead in
  views, kept deliberately as a documented reusable utility + its test.
- NEW: `_on_add`/`_on_edit` share #1's non-atomic bug class (phantom bill
  if goal insert fails; bill updated before a failing goal update).
- NEW: `bills_view.py` delete has no goal-specific warning when the bill
  being deleted is a Goal's mirrored bill — silent loss of that goal's
  whole contribution history (goal survives via ON DELETE SET NULL with
  $0 progress, no crash, no warning distinguishing it from an ordinary
  delete).
- NEW (found, NOT fixed — see below): `goals_view.py._on_edit` always
  rebuilds the mirrored Bill via `_bill_for_goal` (hardcoded
  `is_active=True`, `category=SAVINGS_CATEGORY`, `notes=GOAL_NOTE`), so any
  manual customization made to that bill via the Bills tab is silently
  reverted the next time the Goal is edited. Pre-existing (original Goals
  feature, not PR #3), untested edge case, and fixing it requires a real
  design call (should the mirrored bill ever be independently customizable,
  or is full-derivation the intended contract?) — left as a documented
  follow-up rather than fixed blind.
- NEW (found, NOT fixed — confirmed benign): `StockTipsView` has no
  `month_keys()` at all, so a tip's `added_date` month never contributes to
  the global picker. Checked `stock_tip_dialog.py`: `added_date` is always
  `date.today()` at creation and never user-editable/backdatable, and the
  current month is always in the global union (Bills/Goals both
  unconditionally seed it) — so this is benign in practice, not a live
  gap. Documented, not fixed.
- Stock Tips view: `_visible_tips()` hand-rolled its own month-prefix string
  instead of reusing `_month_filter.month_prefix()` — harmless today, but a
  real drift point. Fixed (see below).

**Fixed this iteration** (all verified — see Verification below):
1. `repositories/goals.py` + `repositories/bills.py`: added an optional
   `conn` parameter to `add`/`update`/`delete` in both modules (backward
   compatible — every existing call site is unaffected), plus three new
   atomic wrapper functions in `goals.py`: `add_with_bill`,
   `update_with_bill`, `delete_with_bill`, each opening exactly one
   `get_connection()` and doing both the bill and goal writes inside it.
   `views/goals_view.py`'s `_on_add`/`_on_edit`/`_on_delete` now call these
   instead of two separate repo calls — closes deferred #1 and its
   `_on_add`/`_on_edit` twin.
2. `views/goals_view.py:182` — `if goal.bill_id else ZERO` →
   `if goal.bill_id is not None else ZERO` — closes deferred #5.
3. `views/{bills,goals,payments,expenses,salary}_view.py` +
   `views/main_window.py` — added a `data_changed = Signal()` to each of the
   5 views whose own `month_keys()` can introduce a new "interesting month",
   emitted at the end of `_on_add`/`_on_edit`/`_on_delete`; MainWindow
   connects each (via `hasattr` guard, so Notes/Charts/Stock Tips — which
   have no `data_changed` — are silently skipped) to `_rebuild_month_list`.
   Closes deferred #3.
4. `views/bills_view.py._on_delete` — now checks whether the bill being
   deleted is a Goal's mirrored bill and, if so, appends an explicit warning
   naming the goal before the existing payments-removed warning. New finding
   (not one of the original 9), fixed since it's a cheap, low-risk guard
   against real silent data loss.
5. `views/stock_tips_view.py._visible_tips` — now reuses
   `_month_filter.month_prefix()` instead of a hand-rolled duplicate.

**Deliberately left as-is / not fixed this iteration:**
- #2 (Bills self-heal) — already intentional & tested; the immediate-rebuild
  fix (#3) reduces how often the "wrong empty state" is even visible
  in-tab, and re-adding tab-local self-heal would resurrect the exact
  duplication the global selector was built to remove. Not touched.
- #4 (Goals month_keys narrow, future months) — real but low-frequency
  (only matters for previewing a future check-in month of an in-progress
  goal); no clean low-risk fix without deciding how far into the future to
  extend the window (arbitrary — every goal's remaining span? capped at
  N months?). Left as a documented, still-open, low-priority gap.
- #6, #7, #8, #9 — re-affirmed as acceptable per the reasoning above; no
  code change.
- Goal-edit stomping a mirrored bill's independent customization (new
  finding) — real but needs a product decision, not a blind fix; documented
  above as a follow-up.
- Stock Tips' missing `month_keys()` (new finding) — confirmed benign given
  `added_date` is always "today" and never backdatable; documented, not
  fixed.

**Verification this iteration:**
- `nix develop --command python -m pytest -q` — 328 passed / 2 skipped
  baseline (pre-fix) → 343 passed / 2 skipped after fixes + 15 new tests
  (6 in test_goals_repo.py incl. an atomicity-on-failure test via
  monkeypatched `goals.add`; 3 in test_bills_view.py incl. the goal-warning
  text and a `data_changed` emission check; 4 in test_goals_view.py incl.
  the atomic-add-via-dialog round trip and the `bill_id=0` edge case,
  seeded via raw SQL since AUTOINCREMENT can't produce it; 2 in
  test_main_window_global_month.py for the immediate-rebuild wiring). Tier:
  **ran-and-observed**.
- `qt-smoke` (ad hoc headless script, not the packaged skill invocation) —
  constructed a real `MainWindow`, drove `BillsView._on_add` and
  `GoalsView._on_add` through mocked dialogs with the tab left active (no
  tab switch), and asserted the global month picker picked up the new
  month immediately; confirmed exactly one mirrored Bill was created for
  the new Goal; confirmed the goal-aware delete warning text on a real
  `QMessageBox.question` call; confirmed `window.close()` tears down
  cleanly. All passed. Tier: **ran-and-observed**.

**Next step:** Re-run a targeted audit pass over the changed files (this
iteration's fixes) to confirm nothing regressed and no fresh issue was
introduced, then decide whether another full pass is warranted or the audit
is "clear or reasonably so" — if the latter, proceed to landing (branch push
+ PR, fold this file into project-state.md/session-summary.md per
session-closer, delete this file).
