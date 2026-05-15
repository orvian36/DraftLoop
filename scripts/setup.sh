#!/usr/bin/env bash
# DraftLoop one-shot setup.
# Installs uv + pnpm, syncs workspaces, optionally downloads ML models.
set -euo pipefail

usage() {
  cat <<EOF
Usage: scripts/setup.sh [--no-models] [--no-docker] [--help]

  --no-models   Skip HHEM weight download (added by Plan 3)
  --no-docker   Skip Docker-related setup (added by Plan 7)
  --help        Show this message
EOF
}

WITH_MODELS=1
WITH_DOCKER=1
for arg in "$@"; do
  case "$arg" in
    --no-models) WITH_MODELS=0 ;;
    --no-docker) WITH_DOCKER=0 ;;
    --help|-h)   usage; exit 0 ;;
    *)           echo "unknown arg: $arg"; usage; exit 1 ;;
  esac
done

echo "==> ensuring uv is installed"
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "==> ensuring pnpm is installed (via corepack)"
if ! command -v pnpm >/dev/null 2>&1; then
  corepack enable
  corepack prepare pnpm@9.12.0 --activate
fi

echo "==> uv sync (Python workspace)"
uv sync --all-packages

echo "==> pnpm install (JS workspace)"
pnpm install

if [ "$WITH_MODELS" = "1" ]; then
  echo "==> model downloads deferred until Plan 3 (HHEM)"
fi

if [ "$WITH_DOCKER" = "1" ]; then
  echo "==> docker setup deferred until Plan 7"
fi

echo "==> setup complete"
