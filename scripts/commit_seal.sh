#!/usr/bin/env bash
# Commit integration/removal.seal alone, only if it is new or changed (safe to re-run).
set -euo pipefail
SEAL="${1:-integration/removal.seal}"
git add -- "$SEAL"
if git diff --cached --quiet -- "$SEAL"; then
  echo "$SEAL is already committed and unchanged; nothing to commit"
  exit 0
fi
git commit -q -m "chore: seal the removal list" -- "$SEAL"
