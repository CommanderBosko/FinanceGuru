# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

## Session: 2026-09-03 — Notes Tab + Global Month Selector (PR #3)

**Focus**: Add a Notes tab (freeform monthly journal entries, Bills-picker-style), then unify all 7 tabs' local month pickers into one global toolbar selector.

### What changed (and why)
- **Notes tab shipped in two layers**: data first (`Note` model, schema, repository — `65a8830`), then the view (`d284537`) plus the Goals/Bills changes it depends on (`select_month()`, a delete-cascade Yes/No/Cancel prompt when notes link to the item being deleted). A note files under whichever month is currently selected (not necessarily today's), so backfilling a past month works; a linked note shows a "→ Name" indicator whose click switches tabs and drives the target's month to the linked item's own relevant month.
- **Groundwork for one global picker**: every month-aware tab (Bills, Payments, Expenses, Income, Goals, Notes, Charts, Stock Tips) got a shared `month_keys()`/`select_month()`/`select_all()` contract (`2fbe434`) without changing any tab's own filtering *rule* — pure wiring change, each still independently tested. Then a single `QComboBox` in a `MainWindow` toolbar row (`659c896`) replaced the 7 tabs' own local pickers, its entry list the union of all 8 tabs' `month_keys()`, rebuilt on tab-switch/DB-restore but only re-broadcast when the selection actually changes.
- **Two bugs caught by a pre-merge full-diff `/code-review high` pass on the whole PR** (not just the last commit): (1) a Goal's mirrored-bill-linked note wasn't counted or actually deleted by `GoalsView`'s delete-cascade prompt, since it only checked the direct `goal_id` link — fixed same-session (`81e207a`), the button's own "Yes" label had been silently lying; (2) clicking a note's cross-month link left every *other* month-aware tab silently showing a stale month next to the now-desynced toolbar, because `_rebuild_month_list`'s change-detection compared the toolbar's own already-synced value against itself — fixed via a new `skip` param on `_broadcast_month` (`d5d0ece`).
- **9 more findings from that same review were deliberately deferred**, not fixed — pre-existing patterns, narrow edge cases, or already-accepted trade-offs. Full backlog with file:line locations saved to memory (`global-month-selector-followups`) rather than left to rot in a closed PR's review comments.
- Merged as PR #3 (`c2079b802`). 328 tests, up from 240.

### Decisions
- Notes' month is the explicitly-selected picker month, never derived from `created_at` — deliberate backfill support.
- `bill_id`/`goal_id` stayed two hardcoded nullable FKs rather than a general `entity_type`/`entity_id` link mechanism — simplest fit for exactly two targets today; flagged as a scaling cost if a third ever shows up.
- Global picker re-broadcasts only on actual selection change (not every tab switch) — avoids an eight-tab refresh storm on routine navigation; accepted as negligible-cost on a two-user local-SQLite app even where it does fire unconditionally.
- Only the cross-tab-navigation staleness bug got fixed pre-merge; the other 9 review findings were triaged and deferred rather than either blocking the merge or being rushed in without proper care.

### Issues / surprises
- The Goal-mirrored-bill note-undercounting bug was in code from two commits *earlier this same session* (`d284537`), not a hidden pre-existing bug — caught by review before it ever reached `main`.

### Next session
- Work the `global-month-selector-followups` backlog: highest-value are `goals_view.py:296` (non-atomic Goal+mirrored-Bill delete) and `main_window.py:257` (global month list doesn't rebuild until a tab switch after a same-tab CRUD change).
- Unrelated carry-forward items unchanged: natalie-laptop `nix flake update` + rebuild, a real-display GUI eyeball of Charts/Expenses, Windows/macOS/Flatpak hardware verification, multi-user data partitioning.

**Commits**: `65a8830..d5d0ece` (5 commits, merged as `c2079b8`)

---

## Session: 2026-08-31 — `/improve-system` via `manager` agent (skill-tooling only)

**Focus**: Close out a gap since the 2026-08-16 close-out — no app code changed; the only landed work was a `manager`-agent-run `/improve-system` sweep across the Claude-skill layer.

### What changed (and why)
- **`/improve-system` run end-to-end by the `manager` agent** (user asked for it explicitly), deciding every "confirm structural" gate itself per `~/.claude/manager-profile.md`. Landed as PR #2 (`chore/improve-system-2026-08-31` → squash-merged `4e06c47`), after watching real CI (flake-check, macos-package, flatpak-check, windows-package) to completion before merging.
- **Real bug fixed**: `qt-visual-verify`'s documented headless command (`QT_QPA_PLATFORM=offscreen nix develop --command python <script>.py`) doesn't actually render offscreen — `flake.nix`'s devShell `shellHook` clobbers `QT_QPA_PLATFORM` after the shell starts. Fixed with a new `scripts/run-headless.sh` wrapper (sets the var via `env` *after* `--command` so it survives the shellHook); verified empirically both broken and fixed.
- Two smaller skill-audit fixes: `db-migration`'s re-tag-existing-records decision now goes through `AskUserQuestion` (mutates real financial data); `secret-scan`'s SKILL.md no longer duplicates `scripts/secret-scan.sh`'s config block (pointed at the script as source of truth instead).
- `fewer-permission-prompts` added 4 read-only, ≥3-occurrence Bash entries to `.claude/settings.json`.
- skill-upgrade / skill-suggestion / agent-suggestion / claude-rules all came back clean.

### Decisions
- Fixed `qt-visual-verify` with a root-cause wrapper script rather than patching the wrong inline command in the docs.
- Declined a `config.json` for `secret-scan` (would need matching `create-secret-scan` support, out of this project's scope) in favor of pointing prose at the existing script.

### Issues / surprises
- A first attempt at this same `/improve-system` run, in an earlier session that day, hit a permission/mode boundary the manager agent needed to flip to proceed autonomously — a designed hard boundary, correctly not routed around via a different tool. It offered to run directly instead or wait for the user to flip the mode interactively, and stopped there. A retry in a fresh session succeeded.
- Session-closer's own transcript-cutoff detector (`find-last-skill-invocation.sh`) again mis-detected the last close — it reported a cutoff of 2026-08-31, but the actual last `chore(session)` commit was 2026-08-16. Fell back to the git-log baseline per the documented gotcha and mined all 6 intervening transcripts by hand; only the one commit above resulted from any of them.

### Next session
- No app-facing next steps opened this session — see `project-state.md`'s Next Steps (natalie-laptop rebuild, Charts GUI eyeball, non-Linux hardware verification, multi-user partitioning) for what's actually open.

**Commits**: `4e06c47` (1 commit)

---

## Session: 2026-08-16 — Currency Converter Tab + Tab Reorder

**Focus**: Add a Currency Converter tab (two "Name (Country)" dropdowns, live rates), then reorder tabs alphabetically with Dashboard pinned first.

### What changed (and why)
- **New Currency Converter tab** — Amount field, From/To dropdowns over ~31 major currencies ("Pound (England)" style), a swap button, and a live result. Rates come from the free/keyless Frankfurter API, cached in a new `currency_rates` table with an offline fallback, and a new generic `preferences` key/value table remembers the last-used From/To/amount across restarts (first use of that mechanism, written reusable).
- **Real bug found only by hitting the live API**: Frankfurter's documented `api.frankfurter.app` host now redirects to `api.frankfurter.dev/v1`, and Cloudflare 403s the default Python `urllib` User-Agent as a bot signature. Fixed by calling the new host with a real User-Agent.
- **Full `/audit` pass** (security-review + code-review + project risk checklist, required by `new-feature`'s checklist for money math + external data) found and fixed 9 issues: a QThread-teardown gap missing `prices.py`'s unbounded-wait fallback (real crash-on-quit risk on a hung DNS lookup); `refresh()` wrongly triggering a network fetch and not reloading preferences after a DB restore; zero-decimal-currency display (JPY/KRW/ISK); a cache-write failure freezing the UI mid-fetch; a stale saved currency falling back to the wrong default; a double-fire swap; and preferences writes opening 3 DB connections instead of 1.
- **Tab reorder** — alphabetical with Dashboard pinned first (Dashboard, Bills, Charts, Currency Converter, Debt Snowball, Expenses, Goals, Income, Payments, Stock Tips, Stocks). Caught and fixed one test (`test_views_smoke.py`'s `EXPECTED_TABS`) that pinned the old order.

### Decisions
- `refresh()` kept strictly DB-local (no network) to match the Stocks/Stock Tips contract — only initial construction and the explicit "Refresh Rates" button trigger a live fetch.
- `currency_rates`/`preferences` both excluded from `_CORE_TABLES` so older backups without either table still restore and gain them on the next `init_db()`.
- The tab reorder skipped the `/interview` ceremony as a simple, unambiguous request, per that skill's own exception for well-scoped trivial changes.

### Issues / surprises
- The Frankfurter host redirect + Cloudflare User-Agent block (above) — not documented anywhere, only found by actually driving the live API during `qt-smoke`/`qt-visual-verify`.

### Next session
- No app-facing next steps opened this session — see `project-state.md`'s Next Steps (natalie-laptop rebuild, Charts GUI eyeball, non-Linux hardware verification, multi-user partitioning) for what's actually open.

**Commits**: `0cb13c4..3968f5e` (2 commits)

---

## Session: 2026-08-03 — Bills Month/Year Filter + Goal Gating, Windows CI Fix, qt-visual-verify Skill

**Focus**: User asked how the Goals `start_date` feature worked, noticed a future-dated Goal's bill showing on the Bills tab immediately, and asked whether that was a `start_date` bug or a bigger gap.

### What changed (and why)
- **Diagnosed as the bigger problem**: `BillsView` listed every bill unconditionally with no month concept at all (unlike Payments/Income, which already had month/year dropdowns), and `GoalsView` never passed `start_date` to the linked bill it auto-creates. Fixing only the second half would have had nowhere to take effect.
- **Bills gained a month/year `QComboBox`** (via `/interview` to pin the exact semantics first) — defaults to the current month, built from "interesting" months (today, one-time due months, yearly this/next-year due months, goal start/target months), filtering via `Bill.is_due_in`. A goal-specific gate lives in `BillsView` itself (cross-references `repositories/goals.py`) to hide a goal's bill until its `start_date` month — no schema change.
- **Follow-up `/audit` pass** found no must-fix issues, 3 minor ones: documented the ascending-vs-Payments/Income's-descending month-picker sort choice, renamed an ambiguous `start` variable to `start_iso`, added a test for the previously-selected-month-vanishing fallback case.
- **Real Windows CI (not local) caught `os.O_NOFOLLOW`** not existing on that platform — crashed `export_all_csv()`'s symlink-race guard with `AttributeError`. Fixed with a `getattr(os, "O_NOFOLLOW", 0)` fallback.
- **New `qt-visual-verify` project skill** — screenshot-and-actually-look verification, distinct from `qt-smoke`'s functional-only checks; built via `/skill-suggestion` after the same hand-rolled pattern turned up in 9 of 11 recent sessions.
- **`.claude/settings.local.json` added to the repo's own `.gitignore`** — previously excluded only via this machine's global git config; now any contributor gets the same exclusion without it.

### Decisions
- `start_date` kept off the `Bill` model entirely, per the user's explicit interview answers — the goal-bill gate lives in `BillsView` only.
- Bills' month picker sorts oldest-first (unlike Payments/Income's newest-first) — accepted as-is, since Bills mixes past *and* future months.

### Issues / surprises
- This session also touched the separate NixOS repo (a `skill-upgrade` gotcha fix to `session-closer`'s transcript-cutoff detector, committed there as `2ed3644`) — unrelated to FinanceGuru's own history, noted here so it isn't mistaken for missing work.

### Next session
- No app-facing next steps opened this session — see `project-state.md`'s Next Steps for what's actually open.

**Commits**: `1b96965..6fa44d3` (5 commits)

---

## Session: 2026-08-02 — Month Filters, Sortable Headers, Income Redesign x2, Goals Start Date, Audit Fixes

**Focus**: A day of feature requests handled back-to-back (month/year filters, sortable tables, Income model changes, Goals start date), closed out with a full `/audit` pass.

### What changed (and why)
- **Month/year dropdown filters** replaced the "This month only" checkbox on Payments and Expenses, via a new shared `views/_month_filter.py` module — a plain on/off toggle couldn't browse a specific past month.
- **Click-to-sort headers on every table** (Dashboard, Bills, Payments, Expenses, Income, Stocks, Stock Tips, Goals, Debt Snowball's debts/lump-sum tables). Along the way, found and fixed a real latent bug: every view resolved "the selected row" by indexing a parallel Python list with the table's *visual* row position — correct only until sorting could reorder rows, at which point edit/delete/mark-paid could silently act on the wrong record. Fixed by reading each row's identity back off Qt's `UserRole` item data instead. Verified with a real simulated mouse click on a header (screenshots confirm the sort arrow and correct reordering both directions), not just a programmatic `sortByColumn` call.
- **Income redesigned twice in direct succession.** First commit collapsed the old frequency/pay-days model to a single recurring `pay_day`. Immediately after, adding the same month/year dropdown to Income turned out to be impossible against a bare day-of-month with no year — flagged as a clarifying question rather than forced. The user chose to make Income a dated paycheck log (`pay_date`), reversing the just-shipped design. The upgrade migration wipes pre-existing income rows (no real date to backfill from) rather than guessing — an explicit, flagged, destructive choice.
- **Goals gained a `start_date`** — `monthly_savings()` now spans `start_date → target_date` instead of `today → target_date`, so the required contribution is fixed when a goal is created/edited instead of drifting as time passes. Existing goals backfilled on migration.
- **Full `/audit` pass** (whole-tree, tree was clean) found and fixed 3 real 🔴 bugs: a QThread-destroyed-while-running crash reachable via the row context menu's refresh entry on Stocks/Stock Tips (bypassed the toolbar button's in-flight guard); a Salary "All-time" view producing a nonsense Extra-Spending-Money figure (mixed an all-time total with one month's bill obligation); category rename not re-tagging existing bills/expenses. Plus dashboard `due_day` clamping for goal-mirrored bills in short months, de-duplicated month-picker code, consistent repository `add()` return types, and one hardening fix (backup/CSV-export symlink-following — verified confidence only 3/10, not realistically exploitable, but a free one-line fix). Security-vulnerability identification found 6 candidates; parallel false-positive-verification on the 3 most plausible filtered all of them out.

### Decisions
- Income's design reversal was a deliberate correction once the month-filter requirement exposed a gap, not a mistake — both commits were sound given what was known when each was made.
- Row-selection fix was done as one consistent pattern by a single agent across every view, not parallelized — divergent implementations risked real data-integrity bugs (editing the wrong record).
- Debt Snowball's payoff-plan/schedule tables stay unsorted, per the user's call — they're computed, time-ordered output, not a browsable record list.
- The audit's 5 independent fixes were parallelized across sub-agents (disjoint file sets); the small, already-understood `db.py` symlink hardening was done directly instead of spawning a 6th agent.

### Issues / surprises
- This session-closer run was itself interrupted once mid-close: the first pass only skimmed the tail of a 13-transcript scan and mistook an old (2026-07-16) close narrative for current context. The transcript-cutoff helper (`find-last-skill-invocation.sh`) had also picked a stale marker (2026-07-16) instead of the real last close (2026-07-26, confirmed via the `chore(session)` commit `f7f0549` and the existing session-summary entries below) — worth a `skill-upgrade` look at why the detector drifted.
- 5 of the 6 commits were pushed mid-session (once asked for, after the Goals start-date commit); the final audit-fix commit was left local and is pushed by this close-out.

### Next session
- No app-facing next steps opened this session — see `project-state.md`'s Next Steps (natalie-laptop rebuild, Charts GUI eyeball, hardware verification of non-Linux builds, multi-user partitioning) for what's actually open.

**Commits**: `8909011..d25bfe4` (6 commits)

---

