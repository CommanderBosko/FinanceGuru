#!/usr/bin/env bash
# Mechanical step 1 of audit: print the three fixed git commands that
# determine what to review. Interpretation of which case applies stays in
# the SKILL's prose.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "--- git status --short ---"
git status --short

echo "--- git diff --stat (working tree) ---"
git diff --stat

echo "--- git diff --stat main...HEAD (branch vs main) ---"
git diff --stat main...HEAD 2>/dev/null || echo "(not applicable — no main to compare, or already on main)"
