#!/usr/bin/env bash
# 3/3 Start the frontend: the e2ekg Next.js UI on http://localhost:3000. The browser talks only to
# Next, which proxies /api/* to the backend (scripts/start-backend.sh, default http://127.0.0.1:8000).
#   scripts/start-frontend.sh
#   PORT=3100 scripts/start-frontend.sh
#   API_URL=http://127.0.0.1:9000 scripts/start-frontend.sh
#   PROD=1 scripts/start-frontend.sh            # production build + start
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ -d "$ROOT/external/e2ekg/ui" ]] || { echo "e2ekg is not set up: run scripts/setup.sh first" >&2; exit 1; }
cd "$ROOT/external/e2ekg"
exec bash scripts/start-ui.sh
