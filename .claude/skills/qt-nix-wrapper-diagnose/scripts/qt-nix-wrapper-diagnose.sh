#!/usr/bin/env bash
# Mechanical steps 1-4 of qt-nix-wrapper-diagnose: build, inspect the wrapper
# chain, grep its baked-in env vars, and live-run the binary. Prints
# everything needed for the SKILL's step-5 interpretation; does no
# interpretation itself.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "--- 1. build ---"
OUT=$(nix build .#default --no-link --print-out-paths)
echo "store path: $OUT"

echo "--- 2. bin directory ---"
find "$OUT/bin" -maxdepth 1

echo "--- 3. baked-in env vars (outermost wrapper) ---"
nix develop -c bash -c "strings '$OUT/bin/financeguru' | grep -E 'QT_PLUGIN_PATH|LD_LIBRARY_PATH|QT_QPA|XDG_DATA_DIRS'" || echo "(no matches)"

echo "--- 4. live run ---"
LOG=$(mktemp)
set +e
timeout 5 "$OUT/bin/financeguru" >"$LOG" 2>&1
STATUS=$?
set -e
echo "exit: $STATUS"
echo "log:"
cat "$LOG"
rm -f "$LOG"
