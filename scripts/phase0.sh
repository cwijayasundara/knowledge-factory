#!/usr/bin/env bash
# Phase 0 runbook as a script: apply the e2ekg patches, generate curation and held-out data, check the
# removal list, seal it, record the starved baseline, collect flags. See docs/RUNBOOK.md.
#
#   bash scripts/phase0.sh            print every command; run the steps that call no LLM; stop at the first LLM step
#   bash scripts/phase0.sh --plan     only print every command
#   bash scripts/phase0.sh --yes      also run the steps that call an LLM (needs FIREWORKS_API_KEY; costs money)
#
# Non-destructive: it never deletes data, regenerates nothing that exists (e2ekg's generator refuses a
# non-empty output dir, so a seed already on disk is skipped), and commits only integration/removal.seal.
# It does not write evalx/removal.yaml: that is the owner's decision (step 4 of the runbook).
set -euo pipefail
unset VIRTUAL_ENV

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

YES=0 PLAN=0
for a in "$@"; do
  case "$a" in
    --yes) YES=1 ;;
    --plan) PLAN=1 ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

# Seeds come from the code, so the script cannot drift from kf.evalx.split.
read -r CURATION_SEEDS HELDOUT_SEEDS < <(uv run python -c \
  "from kf.evalx.split import CURATION_SEEDS as c, HELDOUT_SEEDS as h; print(','.join(map(str, c)), ','.join(map(str, h)))")
E2EKG_DIR="$ROOT/external/e2ekg"
# Preprocess chat labels: scripted needs no network. Set PREPROCESS_LLM=fireworks (and pass --yes) to use GLM.
PREPROCESS_LLM="${PREPROCESS_LLM:-scripted}"
RUNS=3

step() { printf '\n==> %s\n' "$*"; }
show() { printf '+'; printf ' %q' "$@"; printf '\n'; }
# run CMD...: print it, run it unless --plan.
run() { show "$*"; [[ $PLAN == 1 ]] || "$@"; }
# run_llm CMD...: print it; run it only with --yes (and not --plan).
run_llm() {
  show "$*"
  if [[ $PLAN == 1 ]]; then return 0; fi
  if [[ $YES != 1 ]]; then echo "  (calls an LLM: not run without --yes)"; return 0; fi
  "$@"
}
e2ekg() { (cd "$E2EKG_DIR" && uv run e2ekg "$@"); }

step "1. Apply the e2ekg pin and patches (integration/apply.sh)"
run bash integration/apply.sh

gen_seed() {  # gen_seed <data_root_prefix> <seed>
  local root="$ROOT/$1/seed-$2"
  step "Data for $1/seed-$2: generate, preprocess, ledger, harvest (full and as-of)"
  if [[ -d "$root/raw" && -n "$(ls -A "$root/raw" 2>/dev/null)" ]]; then
    echo "$root/raw already generated; skipping (delete it yourself to regenerate)"; return
  fi
  show "e2ekg generate --scenario all --seed $2 --out $root/raw"
  [[ $PLAN == 1 ]] || e2ekg generate --scenario all --seed "$2" --out "$root/raw"
  show "e2ekg preprocess --scenario all --raw $root/raw --out $root/processed --llm $PREPROCESS_LLM"
  show "e2ekg ledger --scenario all --raw $root/raw --out $root/processed"
  show "e2ekg harvest --scenario all --proc $root/processed --out $root/graph"
  show "e2ekg harvest --scenario all --proc $root/processed --out $root/graph --as-of"
  [[ $PLAN == 1 ]] && return
  if [[ "$PREPROCESS_LLM" == fireworks && $YES != 1 ]]; then
    echo "  (PREPROCESS_LLM=fireworks calls an LLM: not run without --yes)"; return
  fi
  e2ekg preprocess --scenario all --raw "$root/raw" --out "$root/processed" --llm "$PREPROCESS_LLM"
  e2ekg ledger --scenario all --raw "$root/raw" --out "$root/processed"
  e2ekg harvest --scenario all --proc "$root/processed" --out "$root/graph"
  e2ekg harvest --scenario all --proc "$root/processed" --out "$root/graph" --as-of
}

step "2. Curation data (flags and trails come from these seeds only): CURATION_SEEDS=$CURATION_SEEDS"
for s in ${CURATION_SEEDS//,/ }; do gen_seed data_curation "$s"; done
step "3. Held-out data (scoring only): HELDOUT_SEEDS=$HELDOUT_SEEDS"
for s in ${HELDOUT_SEEDS//,/ }; do gen_seed data_heldout "$s"; done

step "4. Removal list: evalx/removal.yaml (written by the owner, then sealed)"
if [[ ! -f evalx/removal.yaml ]]; then
  echo "evalx/removal.yaml does not exist. Write it (see docs/RUNBOOK.md step 4), then run this script again." >&2
  [[ $PLAN == 1 ]] || exit 1
fi
if [[ $PLAN != 1 ]] && ! uv run python -c "import sys; from pathlib import Path; from kf.evalx.removal import RemovalList; sys.exit(0 if RemovalList.load(Path('evalx/removal.yaml')).items else 1)"; then
  echo "evalx/removal.yaml has no items (it is still the template). Write the list first." >&2
  exit 1
fi
step "5. Seal it (refuses if the seed bundle already holds a removed text), commit the seal alone"
run uv run kf seal
run git add integration/removal.seal
run git commit -m "chore: seal the removal list" -- integration/removal.seal

step "6. Baseline: starved graph arm on the held-out seeds, $RUNS runs per scenario"
run_llm uv run kf eval run --arms graph --starve --heldout --runs "$RUNS"

step "7. Flag collection: graph_kb on the curation seeds (starved, same switch as the baseline)"
run_llm uv run kf eval run --arms graph_kb --starve --runs "$RUNS"

step "Stop. Phase 0 exit: flags exist (uv run kf flags list), baseline stored, seal committed."
echo "Owner: copy the baseline's scores into state/baseline.json (see docs/RUNBOOK.md)."
