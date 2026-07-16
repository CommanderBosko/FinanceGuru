# Session Summary — Finance Guru

_Older entries are in [session-summary-archive.md](session-summary-archive.md)._

---

## Session: 2026-07-16 — Improvement Sweep (Trend Chart, Filters, Multi-System Flake)

**Focus**: User delegated an open-ended improvement pass — "take a deep look, implement all of them one by one, verify, commit."

### What changed (and why)
- **Net-worth trend chart** — the Charts tab now has Spending / Net Worth sub-tabs; the new chart finally shows the snapshots accruing since 2026-07-02. `snapshots.trend_segments()` (pure, unit-tested) breaks the line wherever adjacent snapshots are >7 days apart and a scatter overlay dots every point, so days the app never ran render as honest gaps instead of interpolation. This was project-state's short-term goal #1.
- **Expenses tab filters** — "This month only" checkbox + live search, copied from the Payments pattern; expenses accumulated forever with no way to narrow them. First behavioral view tests added (`test_expenses_view.py`).
- **Multi-system `flake.nix`** — packages/checks/devShells now generated per-system (`forAllSystems`, x86_64-linux + aarch64-linux) so an ARM machine could consume the flake unchanged; derivations identical, NixOS-side path untouched.
- **One `money()` formatter** — the Expenses tab had drifted to `$1234.56`; all ~40 money displays across twelve view modules now route through `views/_table.money()`.
- **CI confirmed green** on the real GitHub runner (first real `qt-launch` runs included) — closed old Next Steps #2 with no change.

### Decisions
- Skipped the interactive `/interview` — the user's mandate was explicit and complete, and the work was done strictly serially per instruction (each item verified via full pytest before its own commit; `nix flake check` as the final gate).
- Trend gap threshold is 7 days (inclusive), one colour for all segments, Y axis floats around min/max (net worth can be negative), X axis padded a day so a lone snapshot isn't degenerate.
- No Darwin in the flake systems list — PySide6/Qt wrapping there is unproven in nixpkgs and no Mac exists in the fleet.
- money() sweep done fully (scripted regex + hand-checked diff) rather than half-converting — two live idioms would be worse than one.

### Issues / surprises
- None — all four items landed clean; tests 151 → 159, all passing.
- Close-out note: `secret-scan` isn't available in this project's skill list, so the README public-safety pass was a manual grep for secret/IP/MAC patterns over the updated docs (clean).

### Next session
- Rebuild natalie-laptop (`nix flake update financeguru` in the NixOS repo) — still can't launch the app until it gets `517d45e`; the bump also ships this session's sweep.
- Real-display GUI eyeball of the new trend chart + existing charts polish items; decide whether the stacked spending chart should exclude Savings.

**Commits**: `3691ece..1ebac14` (4 commits)

---

## Session: 2026-07-07 (evening) — qt-launch Regression Guard

**Focus**: User asked whether anything else could mitigate the packaged-app Qt bug (fixed earlier this session) from recurring on this or other hosts.

### What changed (and why)
- **Added `checks.qt-launch` to `flake.nix`** — launches the built `packages.${system}.default` binary for real under `xvfb-run` with `QT_QPA_PLATFORM=xcb`, failing `nix flake check` (and CI) if the process doesn't stay running. The prior `package` check only proved the derivation builds, which is exactly why the earlier bug shipped silently — `nix build` succeeded the whole time the app was broken.
- Used `xcb` under a virtual display rather than `offscreen` specifically so the check also exercises the `libxcb-cursor` dlopen path (the other half of the original bug), which `offscreen` wouldn't touch.
- Updated the `qt-nix-wrapper-diagnose` skill to note its manual live-run step is now a debugging aid, not the only gate.

### Decisions
- Verified the check both ways before trusting it: deliberately broke it (bad `QT_QPA_PLATFORM`) to confirm it fails with a useful log, then confirmed it passes on the real fix.

### Issues / surprises
- None — straightforward, scoped addition.

### Next session
- Same as this morning's: bump `financeguru` in the NixOS repo and rebuild natalie-laptop (still pending — this session only added a CI guard, didn't ship the fix to the host).

**Commits**: `cec48ba` (1 commit)

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

