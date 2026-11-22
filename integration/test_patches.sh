#!/usr/bin/env bash
# Apply the e2ekg patches to a fresh clone in a temporary directory and run the tests the
# patches add (tests/agent/test_kf_wiring.py, tests/evals/test_kb_arm.py). Extra arguments go
# to pytest, e.g. `bash integration/test_patches.sh tests/agent tests/evals` for the full suites.
set -euo pipefail
unset VIRTUAL_ENV

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

E2EKG_DIR="$TMP/e2ekg" bash "$REPO/integration/apply.sh"
cd "$TMP/e2ekg"
if (( $# )); then
  uv run pytest -q "$@"
else
  uv run pytest -q tests/agent/test_kf_wiring.py tests/evals/test_kb_arm.py
fi
