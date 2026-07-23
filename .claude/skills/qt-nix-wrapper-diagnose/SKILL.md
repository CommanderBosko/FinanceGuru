---
name: qt-nix-wrapper-diagnose
description: Verify that FinanceGuru's Nix-packaged app (packages.${system}.default in flake.nix) actually has a working Qt runtime environment, by inspecting the built wrapper directly and running it — not just trusting that `nix build` succeeded. Use when the user says "diagnose the Qt wrapper", "check the packaged app's Qt env", "why won't the built app find a Qt platform plugin", "qt-nix-wrapper-diagnose", or "verify the flake package launches".
---

# Qt Nix Wrapper Diagnose

Verify (and, if broken, fix) that the packaged FinanceGuru app's `wrapQtAppsHook` wrapping actually sets a working Qt environment — `nix build` succeeding proves the derivation evaluates, it does **not** prove the app can find a Qt platform plugin at runtime. (Bucket: Verification)

This exists because `wrapQtAppsHook`'s automatic wrap pass can silently fail for `buildPythonApplication` outputs: it wraps `bin/financeguru` (an entry-point stub) *before* Python's own `wrapPythonPrograms` hook rewraps the same file for `PATH`/`PYTHONNOUSERSITE`, and the earlier Qt env vars — including `QT_PLUGIN_PATH` — get dropped from the final wrapper with no error. The first time this happened (2026-07-07), the package built cleanly and the bug only surfaced as "no Qt platform plugin could be initialized" on a real machine (natalie-laptop).

## Steps

1. **Run the mechanical build-and-inspect pass:**
   ```bash
   scripts/qt-nix-wrapper-diagnose.sh
   ```
   (relative to this skill's directory, run from anywhere — it `cd`s to the repo root itself). This does steps 1–4 in one shot: builds `.#default`, lists `$OUT/bin` to show the wrapper chain, `strings`-greps the outermost wrapper for the Qt env vars, and live-runs the binary under a 5s timeout. Confirm it exits `0` and printed all four `--- N. ... ---` sections before trusting its output.

2. **Interpret the bin-directory listing** (its `--- 2. ---` section): expect the visible binary (`financeguru`) plus at least one hidden `.financeguru-wrapped` file. If there were multiple wrap passes (e.g. a `postFixup` wrap on top of the Python wrap), you'll also see `.financeguru-wrapped_` — that's the earlier wrapper, chained.

3. **Interpret the env-var grep** (its `--- 3. ---` section). Confirm:
   - `QT_PLUGIN_PATH` is present and points at a `qtbase`/`.../lib/qt-6/plugins` path.
   - Any runtime-`dlopen`ed libs the platform plugins need are on `LD_LIBRARY_PATH` — at minimum `libxcb-cursor` for xcb/wayland.
   `(no matches)` here means the wrapper is missing the Qt env entirely — go to step 6.
   If there's a wrap chain (step 2 showed `.financeguru-wrapped_`), the script only greps the outermost wrapper; re-run `strings` on each `.financeguru-wrapped*` file by hand if you need to confirm the chain is additive (each wrapper's `setenv`/`prefix` calls survive the `execv` into the next) rather than one overwriting another's vars.

4. **Interpret the live-run result** (its `--- 4. ---` section). Exit code `124` (killed by `timeout`, i.e. it stayed running) with an empty log = success. An immediate exit with a Qt platform-plugin error on stderr = still broken — go to step 6.

   This exact live-run is now automated as the `checks.${system}.qt-launch` derivation in `flake.nix` (added after the 2026-07-07 incident), run under `xvfb-run` with `QT_QPA_PLATFORM=xcb` so it also exercises the `libxcb-cursor` dlopen path, not just plugin-path resolution. It runs on every `nix flake check`, including CI (`.github/workflows/ci.yml`). Steps 1–4 above are still useful for interactive debugging (faster iteration, no Xvfb), but a regression should now fail CI on its own before it reaches a real machine.

5. **Run the full check suite:**
   ```bash
   nix flake check
   ```
   Confirms the `package`, `pytest`, and `qt-launch` checks in `flake.nix` still pass.

6. **If step 3 or 4 shows a missing/broken env var**, the fix pattern (used 2026-07-07) is:
   - Set `dontWrapQtApps = true;` on the `buildPythonApplication` derivation — this disables `wrapQtAppsHook`'s auto-detect pass that gets clobbered.
   - Add an explicit `postFixup` block, which runs *after* Python's own wrap, so the Qt args land on the final wrapper instead of being dropped:
     ```nix
     postFixup = ''
       wrapQtApp "$out/bin/financeguru" \
         --prefix LD_LIBRARY_PATH : ${pkgs.lib.makeLibraryPath [ pkgs.libxcb-cursor ]}
     '';
     ```
     `wrapQtApp` (provided by `qt6.wrapQtAppsHook` in `nativeBuildInputs`) still auto-populates `QT_PLUGIN_PATH`/`XDG_DATA_DIRS` from `buildInputs` even with `dontWrapQtApps` set — you only need to add prefixes for extra runtime-`dlopen`ed libs.
   - Re-run steps 1–5 to confirm the fix actually took.

7. **Report** the final state: which env vars were confirmed present, the live-run result (exit code + log), and the `nix flake check` result. If a fix was applied, name the exact `flake.nix` change made.

## Arguments

None — this skill is hardcoded to FinanceGuru's single `packages.${system}.default` output and its one binary, `bin/financeguru`. It is not parameterized for other binaries or a multi-output flake; if this repo ever grows a second packaged binary, the paths in Steps 2–4 would need to be adapted per-binary.

## Scripts

- `scripts/qt-nix-wrapper-diagnose.sh` — no arguments. Builds `.#default`, lists the bin directory, greps the outermost wrapper for Qt env vars, and live-runs the binary under a 5s timeout, printing all four sections. Called by step 1; steps 2–4 interpret its output.
