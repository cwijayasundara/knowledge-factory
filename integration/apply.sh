#!/usr/bin/env bash
# Clone e2ekg at integration/E2EKG_PIN into external/e2ekg (git-ignored), apply
# integration/e2ekg-patches/*.patch in order with git am, run uv sync there, and install this
# repo editable into that environment so e2ekg can import kf.
#   bash integration/apply.sh                       # into external/e2ekg
#   E2EKG_DIR=/some/dir bash integration/apply.sh   # elsewhere (integration/test_patches.sh)
# An existing clone is reset to the pin (tracked changes discarded) and patched again.
set -euo pipefail
unset VIRTUAL_ENV

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL="${E2EKG_URL:-https://github.com/cwijayasundara/semantic_layers_v2.0}"
DIR="${E2EKG_DIR:-$REPO/external/e2ekg}"
PIN="$(tr -d '[:space:]' < "$REPO/integration/E2EKG_PIN")"
[[ "$PIN" =~ ^[0-9a-f]{40}$ ]] || { echo "E2EKG_PIN is not a full commit sha: $PIN" >&2; exit 1; }

if [[ ! -d "$DIR/.git" ]]; then
  mkdir -p "$(dirname "$DIR")"
  git clone --quiet "$URL" "$DIR"
fi
cd "$DIR"
git cat-file -e "$PIN^{commit}" 2>/dev/null || git fetch --quiet origin
git config user.name "kf integration"
git config user.email "kf@localhost"
git am --abort 2>/dev/null || true
git checkout --quiet --force -B kf-patched "$PIN"
shopt -s nullglob
patches=("$REPO"/integration/e2ekg-patches/*.patch)
(( ${#patches[@]} )) || { echo "no patches in integration/e2ekg-patches" >&2; exit 1; }
git am --quiet "${patches[@]}"

uv sync --quiet
uv pip install --quiet --python .venv/bin/python -e "$REPO"
echo "e2ekg at $PIN + ${#patches[@]} patch(es) in $DIR"
