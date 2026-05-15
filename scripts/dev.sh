#!/usr/bin/env bash
# Boot the dev stack: apps/api (uvicorn reload) + apps/web (next dev).
set -euo pipefail

PORT_API="${PORT_API:-8000}"
PORT_WEB="${PORT_WEB:-3000}"

pids=()
cleanup() {
  echo
  echo "==> stopping dev servers"
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT INT TERM

echo "==> apps/api on :$PORT_API"
(
  cd apps/api
  uv run uvicorn draftloop_api.main:app --reload --host 0.0.0.0 --port "$PORT_API"
) &
pids+=("$!")

echo "==> apps/web on :$PORT_WEB"
(
  PORT_WEB="$PORT_WEB" pnpm -F @draftloop/web dev
) &
pids+=("$!")

wait
