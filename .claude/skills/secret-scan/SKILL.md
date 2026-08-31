---
name: secret-scan
description: Triggers when the user says "secret scan", "scan for secrets", "check for leaked secrets", "is it safe to push", "any secrets in the repo", or "pre-public check". Read-only scan of the working tree and full git history for plaintext secrets, tuned to this project's no-dedicated-scheme setup.
model: haiku
version: 0.1.0
---

# Secret Scan

A read-only guard that scans the **working tree and full git history** for plaintext
secrets before a push or before changing repo visibility.

## Arguments

None.

## What it knows about this project

The values below are a human-readable summary — **`scripts/secret-scan.sh`'s "Project-specific
configuration" block (top of the file) is the actual source of truth.** If you change one, change
the script first and update this summary to match; don't edit these bullets independently.

- **Secret-management scheme:** None. FinanceGuru needs no API keys or credentials — yfinance is used unauthenticated. There is no `.env`, no encrypted secrets directory, no sops/git-crypt/vault.
- **Encrypted/managed secret locations:** N/A — no encryption scheme is configured for this project (`ENCRYPTED_GLOB`/`ENCRYPTED_MARKERS` both empty).
- **Paths excluded from pattern matching:** Only this skill's own directory (`.claude/skills/secret-scan/`), since its docs legitimately contain example secret patterns (`EXCLUDE`).
- **Known intentional non-secrets (don't flag these):** None identified — no real IPs, public keys, or demo tokens are documented anywhere in this repo.
- **Full git-history scan:** Enabled — the repo is small, so a full-history scan is fast and worth the coverage (`SCAN_HISTORY="yes"`).
- **.gitignore coverage checked:** `*.db`, `*.sqlite`, `*.sqlite3` (`GITIGNORE_PATTERNS`) — the user's real financial database, not a credential, but the actual sensitive artifact in this repo.

## Instructions

1. Run `scripts/secret-scan.sh`. It performs four passes:
   - **Working tree** — high-signal patterns (private-key blocks, password hashes,
     GitHub/AWS/Slack tokens) across tracked files, excluding the
     configured paths.
   - **Encrypted-secret integrity** — skipped; no encrypted-secret scheme is configured for this project.
   - **Git history** — the same high-signal patterns across *all commits* (catches
     secrets that were committed then removed but still live in history). Prints
     `commit:path` hits. Full history is scanned every run (not skipped) since the repo is small.
   - **.gitignore coverage** — informational check that common secret-file extensions
     are ignored. For this project that means `*.db`, `*.sqlite`, `*.sqlite3` (the user's real financial database — the actual sensitive artifact in this repo, not a credential).

2. Report the result. If **clean**, say so plainly. If there are findings, present each
   with its location and the right remediation:
   - **Plaintext secret in the working tree** → remove it, add the file/pattern to `.gitignore` if it's meant to stay local, and rotate the credential if it was ever pushed.
   - **Unencrypted managed-secret file** → not applicable — this project has no managed-secret scheme.
   - **Secret found in history** (but not the tree) → it was removed but persists in past
     commits. Removing it now is **not** enough for a public repo — rewrite history with
     `git filter-repo --replace-text` (replace the literal with a redaction marker), then
     force-push, then realign other clones (`git fetch && git reset --hard origin/main`).
     Consider rotating the leaked credential regardless.

3. The history pass scans every commit, so on a large repo it can take a little time — tell
   the user it's working if it pauses.

## Notes

- Purely read-only; never modifies files or git state.
- Pattern-based, so it's a strong guard, not a proof of absence. Treat a clean result as
  "no high-signal leaks found," and still apply judgment for project-specific secrets.
- To add a new secret pattern, edit `EXTRA_PATTERNS` in `scripts/secret-scan.sh`.

## Script

```
scripts/secret-scan.sh
```
