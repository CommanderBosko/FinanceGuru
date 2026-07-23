---
name: mechanical-sweep-refactor
description: Given a mechanical, grep-identifiable pattern repeated across many files, find every occurrence, generate a disposable script to rewrite them consistently, and verify the result — rather than editing call sites by hand one at a time. Use when the user says "mechanical sweep", "bulk refactor", "sweep and replace X with Y across the codebase", or "rewrite all call sites of X".
---

# Mechanical Sweep Refactor

A grep → generated-script → verify loop for bulk mechanical changes: the same rewrite applied consistently at every call site of some pattern (a call convention, a deprecated helper, an inconsistent formatting expression). (Bucket: Utility)

This is not `simplify` (which cleans up an already-written diff) and not `codebase-improvement-sweep` (which discovers *what* to change across the whole project). Reach for this once the *what* is already named — a specific pattern to replace everywhere.

## Arguments

The whole job hinges on these two inputs, which the user supplies in their request — confirm both before writing a script:

- **Pattern** — the thing to find (a call convention, a deprecated helper, an inconsistent formatting expression), e.g. "every `f'{x:.2f}'` money format" or "every `Optional[X]` type hint".
- **Replacement** — what it becomes, e.g. "route through `money()`" or "`X | None`".

If the user's request only names one side, ask before writing the rewrite script.

## Steps

1. **Enumerate occurrences.** Grep the named pattern across the relevant directories (usually `src/financeguru/`) to find every call site. Read enough surrounding context at a sample of them to confirm the replacement is safe everywhere — if the call sites are too inconsistent in shape for one mechanical rule to apply to all of them, stop and do it as a manual edit instead; this skill is for genuinely uniform patterns only.

2. **Write a disposable rewrite script.** Write a small Python (or `sed`/`awk`) script to the scratchpad directory (never into the repo) that performs the rewrite programmatically across all matched files — string/regex substitution, not per-file manual edits. The script should be idempotent (safe to re-run) and should only touch lines matching the pattern.

3. **Run the script.**

4. **Spot-check the diff.** Run `git diff` and review it — check a sample across different files (not just the first one) to confirm every occurrence was rewritten correctly and nothing unrelated changed. If anything looks wrong, fix the script and re-run rather than hand-patching the output.

5. **Verify.** Run `nix develop --command python -m pytest -q`. If the pattern touches a view or dialog's GUI-visible behavior, also invoke `qt-smoke`.

6. **Report and hand off.** Report the number of files and call sites changed. If the user wants it committed, invoke the `git-commit` skill — don't commit the disposable script itself.

## Gotchas

- **Don't force a non-uniform pattern through this.** If call sites vary enough that the "mechanical" rewrite would need per-site judgment calls, that's a sign this is a manual refactor, not a sweep — do it by hand instead.
- **The rewrite script is disposable.** It lives in the scratchpad, gets deleted or ignored afterward, and never gets committed alongside the change it produced.
- **Spot-check across multiple files, not just one.** A script that looks right on the first match can still mis-handle a different call-site shape later in the list.
