---
name: watch-ci
description: After pushing to a branch, find the matching GitHub Actions run, watch it to completion, and report per-job pass/fail — pulling failed-step logs automatically instead of a second manual round of `gh` calls. Use when the user says "watch ci", "watch the run", "check if CI passed", "babysit this push", or "watch-ci".
---

# Watch CI

Watch the GitHub Actions run for the current (or a given) branch/commit to completion and report results. (Bucket: Verification)

## Arguments

- `branch` (optional) — the branch to watch. Defaults to the current branch if the user doesn't name one.
- `run-id` (optional) — a specific run ID or URL the user already has. Skips run discovery and watches it directly.

## Steps

1. Confirm the target: if the user didn't name a branch, use the current branch. If they gave a specific run URL or ID instead, use that directly.
2. Run `scripts/watch-ci.sh [branch] [run-id]` from the repo root. It resolves the run for the branch's current commit — retrying for up to ~30s to cover the brief delay between a push and GitHub creating the run, then falling back to the most recent run on that branch if still no exact SHA match — streams `gh run watch` live, then prints per-job conclusions. If the run failed, it also prints the failed step's logs.
3. Report to the user:
   - Overall result (success/failure) and which job(s), if any, failed.
   - If failed: read the failed-step log output the script printed and summarize the likely root cause in a sentence or two — don't just paste the raw log back.
   - If the script printed a fallback WARNING (the watched run's commit doesn't match HEAD), surface that plainly — the result may be for a stale run, not the latest push.
4. Do not automatically rerun the workflow or push a fix. Re-running or pushing are consequential actions — report findings and let the user decide (rerun via `gh run rerun <id>`, fix and push again, etc.).
5. If `gh` reports no runs at all for the branch (e.g. push hasn't triggered a workflow yet, or the branch has no matching workflow trigger), say so plainly rather than retrying silently.

## Scripts

- `scripts/watch-ci.sh [branch] [run-id]` — resolves the run ID for a branch, retrying briefly to cover the post-push run-creation race before falling back to the most recent run (and warning if that fallback's commit doesn't match HEAD). Watches it with `gh run watch --exit-status`, prints per-job conclusions via `gh run view --json jobs`, and on failure prints `gh run view --log-failed`. Exits with the same status as `gh run watch`. Called by step 2.
