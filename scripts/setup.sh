#!/usr/bin/env bash
# 1/3 Set up everything for manual testing: Python env, OKF validator, the patched e2ekg checkout,
# its ingested knowledge graph, the UI's npm packages, and a check of the seed bundle.
#   scripts/setup.sh                      # hero scenario only (fast, enough to try the UI)
#   scripts/setup.sh --scenario all       # all 7 scenarios (slow)
#   scripts/setup.sh --clean              # rebuild the e2ekg data from scratch
# Safe to re-run. An existing external/e2ekg is left alone: re-applying the patches can change its
# commit sha and invalidate a G2 measurement (see docs/RUNBOOK.md). Delete external/e2ekg and re-run
# to rebuild it from integration/E2EKG_PIN.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

SCENARIO=hero CLEAN=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --scenario) SCENARIO="$2"; shift 2 ;;
    --clean) CLEAN=(--clean); shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done
step() { printf '\n==> %s\n' "$*"; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "missing '$1': $2" >&2; exit 1; }; }

step "Prerequisites"
need uv "install from https://docs.astral.sh/uv/"
need git "install git"
need node "Node 20+ is needed for the UI"
need npm "comes with Node"
[[ "$(node -p 'process.versions.node.split(".")[0]')" -ge 20 ]] || { echo "Node 20+ required (found $(node -v))" >&2; exit 1; }

step "Python environment (kf)"
uv sync

step "OKF validator (external/okf)"
bash scripts/fetch_okf.sh

step "e2ekg checkout (pinned, patched with the kf tools)"
if [[ -d external/e2ekg/.git ]]; then
  echo "external/e2ekg already present, leaving it as is"
else
  bash integration/apply.sh
fi

step "API key"
if grep -qs '^FIREWORKS_API_KEY=.' .env; then
  echo ".env has FIREWORKS_API_KEY (AutoRCA and the curator can run)"
else
  echo "!! no FIREWORKS_API_KEY in .env: the graph, ontology and bundle views work, LLM runs do not."
  echo "   Add it with:  echo 'FIREWORKS_API_KEY=fw_...' > .env"
fi
# e2ekg's scripts read .env from its own directory
[[ -f .env && ! -e external/e2ekg/.env ]] && ln -s "$ROOT/.env" external/e2ekg/.env

step "Knowledge graph: ingest scenario '$SCENARIO' into external/e2ekg/data"
(cd external/e2ekg && bash scripts/ingest.sh --scenario "$SCENARIO" --skip-tests ${CLEAN[@]+"${CLEAN[@]}"})

step "Re-install kf into e2ekg's environment (its uv sync removes the editable install)"
uv pip install --quiet --python external/e2ekg/.venv/bin/python -e "$ROOT"

step "UI packages (external/e2ekg/ui)"
(cd external/e2ekg/ui && npm install --no-audit --no-fund)

step "Seed bundle check (kf ci)"
uv run kf ci bundle/

step "Done"
echo "Next:  scripts/start-backend.sh   (terminal 1)"
echo "       scripts/start-frontend.sh  (terminal 2)  ->  http://localhost:3000"
