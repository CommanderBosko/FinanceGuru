# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

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

## Session: 2026-07-26 — watch-ci Skill + Skill-Audit Fixes

**Focus**: User asked to run `/skill-suggestion` and `/skill-upgrade` in sequence, then `/skill-audit` once those landed — three separate skill invocations rather than the bundled `/improve-system`.

### What changed (and why)
- **New project-local `watch-ci` skill** — `/skill-suggestion` mined prior transcripts (no reusable pattern in this session's own empty starting context, since it ran right after `/clear`) and found the same manual `gh run list` → `gh run watch` → `gh run view --json jobs` → `gh run view --log-failed` sequence hand-typed across three sessions (07-03, 07-16, 07-26), including two standalone `sleep`-to-poll attempts the harness's anti-sleep-polling guard blocked. Built to replace that with one invocation.
- **`/skill-upgrade` found nothing to add** — the candidate misfires surfaced by a cross-session transcript scan were already covered by `session-closer`'s existing Gotchas (the `rotate-session-summary.sh` path bug, the `project-state.md` overflow guidance, the `secret-scan`-availability check); the rest were one-off shell slips outside any skill's documented scope, not worth retrofitting a gotcha onto an unrelated skill.
- **`/skill-audit` swept all 9 project-local skills** (including the brand-new `watch-ci`) via 3 parallel sub-agents on disjoint groups, and found 4 real issues, all fixed same-session: `watch-ci`'s run-discovery fallback could silently watch a stale run if GitHub hadn't created the new run yet right after a push (added a ~30s retry loop + a mismatch warning); `secret-scan`'s exclude pathspec was accidentally exempting *all* of `.claude/skills/` from scanning instead of just its own directory (narrowed to match the documented intent); `audit`'s migration checklist duplicated `db-migration`'s whole procedure with nothing forcing them to stay in sync (now cross-references it instead); `audit`'s end-of-report fix-it prompt was free text instead of `AskUserQuestion` (fixed).

### Decisions
- Respected the user's explicit request for three separate skill invocations rather than substituting `/improve-system`, even though it already chains the same skills — the user asked for the granular version this time.
- A sub-agent's claim that `codebase-improvement-sweep` references a nonexistent `TaskCreate` tool was checked against the live tool list and found to be a false positive; dropped rather than "fixed," per the audit skill's own rule not to trust an unverified claim.
- Also saved two memory entries: a new reference memory for the `watch-ci` skill, and an update to the existing "verify real CI, not just local" memory pointing it at the new tool instead of leaving it as an unenforced reminder.

### Issues / surprises
- None — all four fixes were verified before committing (script `bash -n`, a live clean `secret-scan` run with the corrected exclude path).

### Next session
- No app-facing next steps from this session — see the cross-platform packaging entry below and `project-state.md`'s Next Steps for what's actually open.

**Commits**: `48be9b4..a6f0b35` (4 commits)

---

## Session: 2026-07-26 — Cross-Platform Packaging (Flatpak + Windows/macOS)

**Focus**: Ship FinanceGuru beyond NixOS — Flatpak first (locally testable), then Windows/macOS via PyInstaller (CI-only, no local hardware for either).

### What changed (and why)
- **Flatpak packaging** (`packaging/flatpak/`) — manifest on `io.qt.PySide.BaseApp`/`org.kde.Platform`, verified end-to-end locally (`flatpak-builder` build → export → bundle → install → launch) before a CI job was added to build/launch it under Xvfb on every push.
- **Windows + macOS packaging** (`packaging/pyinstaller/`) — a single `sys.platform`-branched PyInstaller spec, built and smoke-launched entirely on GitHub's hosted runners. `main_window.py`'s icon fallback fixed for a PyInstaller freeze (was assuming the Nix source-tree layout, which resolves to nothing once frozen — now uses `sys._MEIPASS`).
- **`DB_DIR` now resolves via `platformdirs`** instead of a hardcoded `~/.local/share` path, with a test proving the Linux path stays byte-identical so bosko/natty's existing production databases aren't orphaned.
- **Three real CI-only bugs, none reproducible locally**, each found only by watching an actual `gh run`: the CI runner never had `flatpak-builder`/`pytest` installed before invoking them; the `flatpak/flatpak-github-actions` action org is deprecated and needs privileged system-level flatpak access a non-root CI user doesn't have (switched to the maintained `flathub-infra` fork, pinned to KDE runtime 6.10); Windows' `platformdirs` resolves the path via the native `SHGetKnownFolderPath` API rather than reading `%LOCALAPPDATA%`, so the env-var-override technique that works on Linux/macOS silently didn't apply — rewritten to assert against the real `LOCALAPPDATA`.

### Decisions
- Code signing (Windows) and notarization (macOS, $99/yr, no free tier) deliberately out of scope — documented as an expected SmartScreen/Gatekeeper bypass step in the README instead.
- This incident is the concrete example behind the "verify real CI, not just local" project memory — local reproduction of a build step proved insufficient three separate times in this session alone.

### Issues / surprises
- All three CI-only bugs above were genuine surprises — each had already been verified thoroughly *locally* before being pushed, and each still failed in the real GitHub Actions environment for reasons no local repro could have caught (missing installs, a deprecated Action, an OS API vs. env-var mismatch).

### Next session
- Get hands-on verification of the Windows/macOS/Flatpak builds on real hardware, or make a deliberate call to accept CI-only verification long-term.
- natalie-laptop still needs `nix flake update financeguru` + rebuild to pick up this and everything since 2026-07-07.

**Commits**: `25c9894..fe7d823` (5 commits + merge)

---

