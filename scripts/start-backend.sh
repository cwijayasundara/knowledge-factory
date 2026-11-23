#!/usr/bin/env bash
# 2/3 Start the backend: the e2ekg FastAPI server (http://127.0.0.1:8000, docs at /docs) with the
# knowledge factory wired in. The graph_kb arm serves the bundle as it is on main right now (a frozen
# snapshot taken at start), and flags the agents file go to state/manual/flags.db.
#   scripts/start-backend.sh
#   API_PORT=9000 scripts/start-backend.sh      # other port (start the frontend with API_URL=...)
#   KF_BUNDLE_REF=kf/<run_id> scripts/start-backend.sh   # serve a curator branch instead of main
# Needs scripts/setup.sh to have run. FIREWORKS_API_KEY comes from .env.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
[[ -d external/e2ekg/data/graph ]] || { echo "no ingested graph: run scripts/setup.sh first" >&2; exit 1; }

REF="${KF_BUNDLE_REF:-main}"
STATE="$ROOT/state/manual"
mkdir -p "$STATE"
if [[ -f .env ]]; then set -a; source .env; set +a; fi

SNAP="$(uv run python - "$REF" "$STATE/snapshots" <<'PY'
import sys
from pathlib import Path
from kf.bundle import serve
print(serve.snapshot(Path("bundle"), Path(sys.argv[2]), commit=sys.argv[1]))
PY
)"
export KF_BUNDLE_SNAPSHOT="$SNAP" KF_STATE_DIR="$STATE"
unset VIRTUAL_ENV   # e2ekg uses its own environment (kf is installed into it by setup.sh)

HOST="${API_HOST:-127.0.0.1}"; PORT="${API_PORT:-8000}"
cd external/e2ekg
# Not e2ekg's start-backend.sh: it runs uv sync, which uninstalls kf from this environment.
.venv/bin/python -c "import kf, fastapi, uvicorn" 2>/dev/null || { echo "kf is missing from e2ekg's env: run scripts/setup.sh" >&2; exit 1; }
export E2EKG_DATA="$PWD/data"
echo ">> bundle: $REF -> $KF_BUNDLE_SNAPSHOT"
echo ">> flags:  $KF_STATE_DIR/flags.db   (read them with: uv run kf flags list --db state/manual/flags.db)"
[[ -n "${FIREWORKS_API_KEY:-}" ]] && echo ">> AutoRCA: enabled (Fireworks)" || echo ">> AutoRCA: disabled (no FIREWORKS_API_KEY in .env)"
echo ">> API on http://$HOST:$PORT   (docs: http://$HOST:$PORT/docs)"
exec .venv/bin/python -m uvicorn e2ekg.api.app:app --host "$HOST" --port "$PORT"
