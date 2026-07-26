#!/usr/bin/env bash
# Find, watch, and report on the GitHub Actions run for a branch/commit.
# Usage: watch-ci.sh [branch] [run-id]
#   branch  - defaults to the current git branch
#   run-id  - skip run discovery and watch this run directly
set -euo pipefail

BRANCH="${1:-}"
RUN_ID="${2:-}"

if [[ -z "$BRANCH" ]]; then
  BRANCH="$(git rev-parse --abbrev-ref HEAD)"
fi

if [[ -z "$RUN_ID" ]]; then
  SHA="$(git rev-parse HEAD)"
  echo "Looking up runs for branch '$BRANCH' (HEAD=$SHA)..." >&2

  # GitHub takes a few seconds to create the run after a push, so retry
  # a few times before concluding there's no matching run yet.
  ATTEMPTS=0
  MAX_ATTEMPTS=6
  until [[ $ATTEMPTS -ge $MAX_ATTEMPTS ]]; do
    RUN_ID="$(gh run list --branch "$BRANCH" --limit 5 \
      --json databaseId,headSha \
      --jq "[.[] | select(.headSha == \"$SHA\")][0].databaseId" 2>/dev/null || true)"
    [[ -n "$RUN_ID" && "$RUN_ID" != "null" ]] && break
    ATTEMPTS=$((ATTEMPTS + 1))
    if [[ $ATTEMPTS -lt $MAX_ATTEMPTS ]]; then
      echo "No run for HEAD yet (attempt $ATTEMPTS/$MAX_ATTEMPTS) — retrying in 5s..." >&2
      sleep 5
    fi
  done

  if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
    FALLBACK_ID="$(gh run list --branch "$BRANCH" --limit 1 --json databaseId --jq '.[0].databaseId // empty')"
    FALLBACK_SHA="$(gh run list --branch "$BRANCH" --limit 1 --json headSha --jq '.[0].headSha // empty')"
    RUN_ID="$FALLBACK_ID"
    if [[ -n "$RUN_ID" ]]; then
      echo "WARNING: no run found for HEAD ($SHA) after ${MAX_ATTEMPTS} attempts; falling back to the most recent run on '$BRANCH', which is for a DIFFERENT commit ($FALLBACK_SHA). This may not reflect your latest push." >&2
    fi
  fi
fi

if [[ -z "$RUN_ID" || "$RUN_ID" == "null" ]]; then
  echo "Could not resolve a run ID for branch '$BRANCH'." >&2
  exit 1
fi

echo "Watching run $RUN_ID..." >&2
set +e
gh run watch "$RUN_ID" --exit-status
WATCH_STATUS=$?
set -e

echo >&2
echo "--- Job results ---" >&2
gh run view "$RUN_ID" --json jobs --jq '.jobs[] | "\(.name): \(.conclusion)"'

if [[ $WATCH_STATUS -ne 0 ]]; then
  echo >&2
  echo "--- Failed step logs ---" >&2
  gh run view "$RUN_ID" --log-failed
fi

exit $WATCH_STATUS
