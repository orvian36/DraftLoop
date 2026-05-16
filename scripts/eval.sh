#!/usr/bin/env bash
# Run the full DraftLoop eval and emit docs/eval-reports/YYYY-MM-DD/
set -euo pipefail

SUITE_ARG=""
OFFLINE=0
for arg in "$@"; do
  case "$arg" in
    --offline) OFFLINE=1 ;;
    --suite=*) SUITE_ARG="${arg#--suite=}" ;;
    --help|-h)
      cat <<EOF
Usage: scripts/eval.sh [--suite=<name>] [--offline]

  --suite=<name>  Run only the named suite (ingest|retrieval|drafting|improvement|end_to_end|cost_budget)
  --offline       Skip suites that require Gemini API access
EOF
      exit 0 ;;
  esac
done

DATE="$(date +%Y-%m-%d)"
OUT_DIR="docs/eval-reports/$DATE"
mkdir -p "$OUT_DIR"

ARGS=(--manifest data/golden/manifest.json --out "$OUT_DIR")
if [ -n "$SUITE_ARG" ]; then ARGS+=(--suite "$SUITE_ARG"); fi
if [ "$OFFLINE" = "1" ]; then ARGS+=(--offline); fi

uv run python -m draftloop_eval "${ARGS[@]}"
echo "==> report written to $OUT_DIR"
