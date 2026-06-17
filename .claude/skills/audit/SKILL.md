---
name: audit
description: One comprehensive code review that orchestrates the security, correctness, and quality lenses, walks FinanceGuru's project-specific risk checklist, proves the code still runs, and consolidates everything into one severity-grouped report. Use when the user says "audit", "audit the code", "comprehensive review", "full review", "review everything", or "do a security/functionality/general audit".
---

# Audit

Run one consolidated review of FinanceGuru that combines the separate review lenses — security, correctness, quality — with this project's own risk checklist, then proves the code still runs and reports findings grouped by severity. This is review-first: present findings and offer to fix; do not start editing without the user's go-ahead.

## Modes

Read the optional argument; default is `full`.

- `audit quick` — fast pass: walk the risk checklist against the diff + run the test suite. Skip `/code-review` and `/security-review`.
- `audit security` — security lens only: `/security-review` + the security items of the risk checklist.
- `audit full` (default) — all lenses below.

## Steps

### 1. Determine scope and show it
- Working-tree diff (default when the tree is dirty): `git status --short` + `git diff --stat`.
- Branch-vs-main (when on a feature branch and the tree is clean): `git diff main...HEAD --stat`.
- Whole-tree (only when explicitly asked, e.g. "audit the whole codebase"): review `src/financeguru/` in full.

State plainly what is being audited before going further.

### 2. Fan out the lenses (full mode)
- **Security:** invoke the `/security-review` skill.
- **Correctness + quality:** invoke `/code-review` at high effort. Do NOT use `/code-review ultra` — it is cloud-based, billed, and user-triggered; only the user launches it. Use the local `/code-review`.
- **Project risk checklist** — walk each against the changed (or relevant) files and record a pass/fail with `file:line`:
  - **SQL injection:** every repository query is parameterized (`?`), never f-string interpolation of user data. Dynamic identifiers (table/column names in `db.py` CSV export & migrations) go through the `_IDENT_RE` allowlist.
  - **File permissions:** DB dir `0o700`; `finance.db`, backups, and exported CSVs `0o600` — these machines are multi-user (bosko/natty).
  - **CSV export:** formula injection defused via `_csv_safe` (neutralizes leading `=`, `+`, `-`, `@`, tab, CR).
  - **Network / yfinance:** tickers validated by `normalize_ticker` before reaching a request URL or the DB; fetched prices/targets sanity-checked finite and `> 0`; raw exceptions go to stderr, never the UI.
  - **QThread lifecycle:** every fetcher thread is stopped on teardown. `MainWindow.closeEvent` drives `stop_threads()` on the views (child widgets in a `QTabWidget` never receive their own `closeEvent`); dialogs stop their fetcher in `done()`; `stop_fetcher` cancels then waits (bounded, then unbounded fallback). Confirm no `QThread` can be destroyed while still running.
  - **Money:** amounts are `Decimal` end to end (`money.to_decimal` / `cents`), stored as REAL, coerced back at the repository boundary — never raw `float` arithmetic on money.
  - **Migrations:** new columns added via `_ensure_column` in `db.py:init_db` (idempotent, identifier-guarded); the `init_db` schema is updated to match; the existing-DB upgrade path is considered.

### 3. Prove it runs
- Run the suite: `nix develop --command python -m pytest -q` — report the pass/fail count.
- If the diff touches `src/financeguru/views/`, also run the **`qt-smoke`** skill (or an inline offscreen smoke) for the affected widget(s) to confirm GUI wiring.

### 4. Consolidate into ONE report
- Dedupe findings that surface from more than one lens.
- Group by severity:
  - 🔴 **correctness/security bug or crash** — must fix
  - 🟡 **minor / edge case / quality** — worth a look
  - 🟢 **clean** — what's holding up well (note the strong points briefly)
- Every finding cites `file:line`.
- End with an explicit offer to fix, and note the user can say "fix all" or "fix N" to proceed.

### 5. Respect the mode
- `quick` → step 1 + risk checklist + step 3 (tests), then report.
- `security` → step 1 + `/security-review` + the security checklist items (SQL, file perms, CSV, network), then report.
- `full` (default) → all of the above.

## Gotchas

- **PySide6 and yfinance only exist inside `nix develop`.** Run all Python/pytest via `nix develop --command ...`. LSP/Pyright "could not be resolved" errors for `PySide6.*` and `yfinance` are expected and not findings.
- **`/code-review ultra` is billed/cloud and user-triggered** — never invoke it from this skill; use the local `/code-review`.
- **Review-first.** Present findings and offer to fix. Don't start editing the working tree until the user gives the go-ahead.
