---
name: qt-nix-wrapper-diagnose
description: Verify that FinanceGuru's Nix-packaged app (packages.${system}.default in flake.nix) actually has a working Qt runtime environment, by inspecting the built wrapper directly and running it — not just trusting that `nix build` succeeded. Use when the user says "diagnose the Qt wrapper", "check the packaged app's Qt env", "why won't the built app find a Qt platform plugin", "qt-nix-wrapper-diagnose", or "verify the flake package launches".
---

# Qt Nix Wrapper Diagnose

Verify (and, if broken, fix) that the packaged FinanceGuru app's `wrapQtAppsHook` wrapping actually sets a working Qt environment — `nix build` succeeding proves the derivation evaluates, it does **not** prove the app can find a Qt platform plugin at runtime. (Bucket: Verification)

This exists because `wrapQtAppsHook`'s automatic wrap pass can silently fail for `buildPythonApplication` outputs: it wraps `bin/financeguru` (an entry-point stub) *before* Python's own `wrapPythonPrograms` hook rewraps the same file for `PATH`/`PYTHONNOUSERSITE`, and the earlier Qt env vars — including `QT_PLUGIN_PATH` — get dropped from the final wrapper with no error. The first time this happened (2026-07-07), the package built cleanly and the bug only surfaced as "no Qt platform plugin could be initialized" on a real machine (natalie-laptop).

## Steps

1. **Build and capture the store path:**
   ```bash
   OUT=$(nix build .#default --no-link --print-out-paths)
   ```

2. **List the bin directory to see the wrapper chain:**
   ```bash
   find "$OUT/bin" -maxdepth 1
   ```
   Expect the visible binary (`financeguru`) plus at least one hidden `.financeguru-wrapped` file. If there were multiple wrap passes (e.g. after a `postFixup` wrap on top of the Python wrap), you'll also see `.financeguru-wrapped_` — that's the earlier wrapper, chained.

3. **Inspect what env vars are actually baked into the outermost wrapper.** `strings`/`file` aren't on the bare host `PATH` — run inside `nix develop`:
   ```bash
   nix develop -c bash -c "strings '$OUT/bin/financeguru' | grep -E 'QT_PLUGIN_PATH|LD_LIBRARY_PATH|QT_QPA|XDG_DATA_DIRS'"
   ```
   Confirm:
   - `QT_PLUGIN_PATH` is present and points at a `qtbase`/`.../lib/qt-6/plugins` path.
   - Any runtime-`dlopen`ed libs the platform plugins need are on `LD_LIBRARY_PATH` — at minimum `libxcb-cursor` for xcb/wayland.
   If there's a wrap chain (step 2 showed `.financeguru-wrapped_`), `strings` each link — the chain should be additive (each wrapper's `setenv`/`prefix` calls survive the `execv` into the next), not one wrapper overwriting another's vars.

4. **Actually run the built binary — a live smoke test, not just a static check:**
   ```bash
   timeout 5 "$OUT/bin/financeguru" > /tmp/fg-wrapper-check.log 2>&1
   echo "exit: $?"; cat /tmp/fg-wrapper-check.log
   ```
   Exit code `124` (killed by `timeout`, i.e. it stayed running) with an empty log = success. An immediate exit with a Qt platform-plugin error on stderr = still broken — go to step 6.

   This exact live-run is now automated as the `checks.${system}.qt-launch` derivation in `flake.nix` (added after the 2026-07-07 incident), run under `xvfb-run` with `QT_QPA_PLATFORM=xcb` so it also exercises the `libxcb-cursor` dlopen path, not just plugin-path resolution. It runs on every `nix flake check`, including CI (`.github/workflows/ci.yml`). Step 4 above is still useful for interactive debugging (faster iteration, no Xvfb), but a regression should now fail CI on its own before it reaches a real machine.

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
