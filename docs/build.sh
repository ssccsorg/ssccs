#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if command -v sdb &> /dev/null; then
    sdb build . --website && exit 0
fi

cat <<'EOF'
sdb not available locally. For native execution, install the following:

  System packages (Ubuntu 24.04):
    build-essential curl git python3 wget ca-certificates

  Additional:
    Quarto CLI        https://quarto.org/docs/download/
    rsync             apt install rsync
    sdb CLI           uv tool install git+https://github.com/ssccsorg/sdbs
    (see https://github.com/ssccsorg/sdbs)

Falling back to Docker execution.
EOF

cd "$(dirname "$0")/.."
exec docker run --rm -v "$(pwd):/work" -w /work/docs ghcr.io/ssccsorg/sdbs:latest sdb build . --website
