---
name: qt-visual-verify
description: Capture and actually look at a screenshot of a headlessly-constructed PySide6 view/dialog/window, driven exactly as a user would against a throwaway database — catches visual bugs (blank/black frames, unreadable palette, broken layout) that qt-smoke's functional checks can't. Use when the user says "qt-visual-verify", "screenshot this view", "show me what it looks like", "visually verify this change", or "capture a screenshot of the GUI".
---

# Qt Visual Verify

Produce and inspect a real screenshot of a PySide6 widget — headless, against a temp database — to confirm a GUI change actually *looks* right, not just that it constructs and behaves. (Bucket: Verification)

This fills a gap `qt-smoke` doesn't cover: `qt-smoke` proves a widget constructs and behaves correctly via assertions, but a widget can pass every assertion while still rendering visually broken (a near-black frame from the offscreen platform's default palette, overlapping widgets, truncated text). This skill exists to catch that class of bug — its output is an image you look at, not a pass/fail assertion.

## Arguments

Every real invocation supplies this context, even though it's usually given as prose rather than a flag:

- **Widget** — which view/dialog/`MainWindow` to screenshot.
- **State(s) to capture** — what's worth a screenshot for this change (e.g. "before vs after adding a goal," each recurrence type, a table with N rows sorted). If the caller doesn't supply this, step 1 asks for it.

## Steps

1. **Figure out what to look at.** From the change under review, decide which widget (view, dialog, or `MainWindow`) and which state(s) are worth a screenshot — e.g. "before vs after adding a goal," "each recurrence type in the dialog," "the table with N rows sorted." If unclear, ask the user what they want to see.

2. **Read `assets/preamble.py` and prepend it verbatim** to a throwaway Python script written under the current session's scratchpad directory — it redirects `db.DB_DIR`/`db.DB_PATH` to a temp dir before `init_db()` (never touch the user's real `finance.db`), constructs the `QApplication`, and forces a readable light palette (the offscreen platform's default can render near-black/illegible screenshots otherwise). Don't retype it by hand — a skipped line breaks the DB isolation or leaves the screenshot unreadable.

3. **Construct the widget and drive it through its real, user-facing API.** Seed data via the repositories (`from financeguru.repositories import bills as bill_repo; bill_repo.add(Bill(...))`), and wherever the interaction itself is what's under test, go through the real dialog/button-handler path rather than skipping straight to internal state — e.g. open the actual `GoalDialog`, set its real widgets, then call the view's real `_on_add` — so the screenshot reflects what a user would actually trigger.

4. **Resize the widget to a sane size and capture.** `widget.resize(900, 300)` (adjust to the widget), then `widget.grab().save(path)` for each state of interest, saving PNGs into the scratchpad directory — one file per state (e.g. `_before.png`, `_after.png`) so they can be compared.

5. **Run the script** with `scripts/run-headless.sh <script>.py` (PySide6 only exists in the dev shell; the wrapper forces a truly offscreen render — see the Gotcha below for why the obvious-looking `QT_QPA_PLATFORM=offscreen nix develop --command python <script>.py` does **not** work here).

6. **Read every saved PNG with the Read tool and actually look at it before reporting anything as verified.** A blank or solid-black frame is a failure to launch, not a pass — don't rely on the script's exit code or stdout alone.

7. **Report back** which widget/states were captured, what each screenshot showed, and flag anything that looks visually wrong even if unrelated to the change under test.

## Gotchas

- **`QT_QPA_PLATFORM=offscreen nix develop --command python <script>.py` does NOT actually go offscreen.** `nix develop`'s `shellHook` unconditionally runs `export QT_QPA_PLATFORM="wayland;xcb"` (`flake.nix`) *after* the shell starts, which clobbers a `QT_QPA_PLATFORM` set as a prefix *before* `nix develop` — verified empirically: that form reports `platformName() == "wayland"`, not `"offscreen"`, and on a machine with no display it would hard-fail instead of rendering. Always use `scripts/run-headless.sh <script>.py` (step 5), which sets the env var via `env` *after* `--command` so it survives the shellHook.
- **PySide6 only exists inside `nix develop`.** Outside the dev shell the import fails; LSP/Pyright "could not be resolved" errors for `PySide6.*` are expected and not real problems.
- **Never run without the temp-DB redirect in the preamble** — a bare `init_db()` writes to `~/.local/share/financeguru/finance.db`, the user's real data.
- **Force the palette.** Without it, offscreen-rendered screenshots can come out solid black/illegible even though the widget is functioning correctly — don't mistake that for a rendering bug.
- **Prefer `qt-smoke` for pure behavioral assertions** (row visibility, table contents, computed getters) — reach for this skill specifically when the point is to *see* the result, not just assert it.

## Assets

- `assets/preamble.py` — fixed setup for every qt-visual-verify script: temp-DB redirect, `QApplication`, and the readable-palette fix. Read it and prepend it verbatim (step 2).

## Scripts

- `scripts/run-headless.sh <script>.py` — runs the script inside `nix develop` with Qt actually forced offscreen (see the Gotcha above for why a naive env-var prefix doesn't work). Called by step 5.
