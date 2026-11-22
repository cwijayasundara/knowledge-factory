#!/usr/bin/env bash
# Clone the OKF repo into external/okf at the commit pinned in integration/OKF_PIN.
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
pin="$(tr -d '[:space:]' < "$root/integration/OKF_PIN")"
dest="$root/external/okf"
if [ ! -d "$dest/.git" ]; then
  mkdir -p "$root/external"
  git clone -q https://github.com/open-knowledge-format/open-knowledge-format "$dest"
fi
if [ "$(git -C "$dest" rev-parse HEAD)" != "$pin" ]; then
  git -C "$dest" fetch -q origin
  git -C "$dest" checkout -q "$pin"
fi
echo "okf at $(git -C "$dest" rev-parse --short HEAD)"
