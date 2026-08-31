#!/usr/bin/env bash
# Run a Python script inside FinanceGuru's dev shell with Qt actually forced
# offscreen. `nix develop`'s shellHook unconditionally runs
# `export QT_QPA_PLATFORM="wayland;xcb"` (flake.nix) *after* the shell starts,
# which clobbers a `QT_QPA_PLATFORM=offscreen` set as a prefix *before*
# `nix develop` — so the documented-looking
# `QT_QPA_PLATFORM=offscreen nix develop --command python script.py` silently
# does NOT go offscreen (verified: platformName() comes back "wayland", not
# "offscreen"). Setting it via `env` *after* `--command` survives the
# shellHook and actually works.
#
# Usage: scripts/run-headless.sh <script>.py
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: run-headless.sh <script>.py [args...]" >&2
  exit 1
fi

cd "$(git rev-parse --show-toplevel)"
exec nix develop --command env QT_QPA_PLATFORM=offscreen python "$@"
