---
name: codebase-improvement-sweep
description: Take a deep, parallelized look across FinanceGuru, find independent improvement opportunities, and implement/verify/commit each one before moving to the next. Use when the user says "improvement sweep", "codebase improvement sweep", "sweep the codebase for improvements", "find improvements and implement them", or "look for improvements and fix them all".
---

# Codebase Improvement Sweep

Find a batch of independent improvements across the project and land each one as its own verified, committed change — rather than one big undifferentiated diff. This is an **Orchestration** skill: it fans out recon, then chains `qt-smoke` and `git-commit` per item.

This is not `audit` (review-only, produces a findings report, never edits code) and not `simplify` (cleans up an already-written diff, doesn't go looking for new work). Run this when the user wants improvements *found and landed*, not just flagged.

## Arguments

- **Scope** (optional) — a specific area the user already named, e.g. "improve the Expenses tab" or "just tests/". When given, don't widen recon beyond it (see Before starting). When omitted, recon runs across the whole project per step 1's area list.

## Before starting

- **Scope it first.** If the user's request is as open-ended as "find improvements," that's fine — the fuzziness is expected here, this skill *is* the scoping mechanism. But if they've already named a specific area (e.g. "improve the Expenses tab"), don't widen the recon beyond it.
- **State the verify plan up front**, per CLAUDE.md: `pytest` for every item, plus `qt-smoke` for any item touching a view/dialog.

## 1. Parallel recon — never sequential

Fan out sub-agents (or parallel `Read`/`Grep` calls) across independent areas of the tree in a single message — do not read files one at a time in sequence. Split along the project's own layering so each piece is genuinely independent:

- `src/financeguru/views/` — UI rough edges, missing filters, inconsistent formatting
- `src/financeguru/repositories/` + `models/` — query inefficiencies, missing validation, dead code
- `tests/` — coverage gaps, flaky or skipped tests
- `flake.nix` / packaging — dependency or build issues
- `reporting.py` / `budget.py` / `categories.py` — money-math or aggregation inconsistencies

Skip any area the user already scoped out. Collect each sub-agent's findings as a short list of candidate improvements with a one-line rationale each — don't let them write code yet.

## 2. Synthesize into independent items

Merge the recon findings into a set of discrete improvement items. Each item must be independently implementable and independently committable — if two findings touch the same lines, merge them into one item rather than creating a merge conflict between two "independent" tasks.

Create one `TaskCreate` entry per item. Drop anything too vague to verify (e.g. "improve code quality" isn't an item; "extract duplicated money-formatting into `money()`" is).

## 3. Per-item loop: implement → verify → commit

Work through the TaskCreate items one at a time (mark each `in_progress` before starting, `completed` after committing):

1. **Implement** the item's change.
2. **Verify:**
   - Always: `nix develop --command python -m pytest -q`
   - If the item touches a view, dialog, or other GUI-visible behavior: also invoke the `qt-smoke` skill
   - If the item touches money math, file I/O, or backup/restore: also invoke `audit`
3. **Commit** via the `git-commit` skill — one commit per item, not one commit for the whole sweep. Summarize the specific change and its verification result in the request to `git-commit`.

If an item fails verification, fix it before moving to the next item — don't let a broken item block or get bundled with the next one's commit.

## 4. Report back

After the loop, summarize: which items were implemented and committed (with commit shas or messages), which were skipped and why, and the overall verification results.

## Gotchas

- **Recon must be parallel.** A prior run of this pattern did 15 sequential single-file `Read` calls before finding anything — a direct violation of CLAUDE.md's parallelization rule. Fan out from the start.
- **One commit per item, not one for the whole sweep.** Bundling defeats the point of independent, individually-verifiable changes and makes a bad item harder to revert cleanly.
- **Don't reach for this when the user wants a report, not changes** — that's `audit`. Don't reach for it when there's already a diff to tidy — that's `simplify`.
