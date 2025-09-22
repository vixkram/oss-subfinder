#!/usr/bin/env bash
set -euo pipefail

BIN="${MASSDNS_BIN:-massdns}"
RESOLVERS="${MASSDNS_RESOLVERS_FILE:-/app/app/resolvers.txt}"

if ! command -v "$BIN" >/dev/null 2>&1; then
  echo "massdns binary not found: $BIN" >&2
  exit 1
fi

if [ ! -f "$RESOLVERS" ]; then
  echo "Resolvers file not found: $RESOLVERS" >&2
  exit 1
fi

if [ $# -lt 1 ]; then
  echo "Usage: $0 <domains.txt> [additional massdns args]" >&2
  exit 1
fi

INPUT="$1"
shift || true

exec "$BIN" -r "$RESOLVERS" -t A -o S -w - "$@" "$INPUT"
