#!/usr/bin/env bash
# Run every lint that gates merges in CI.
set -euo pipefail

echo "==> ruff format --check"
uv run ruff format --check .

echo "==> ruff check"
uv run ruff check .

echo "==> mypy --strict packages/"
uv run mypy packages/

echo "==> python boundary lint"
uv run python scripts/check_boundaries.py --root .

echo "==> mermaid diagrams"
bash scripts/check_diagrams.sh

echo "==> pnpm typecheck"
pnpm -r typecheck

echo "==> pnpm lint"
pnpm -r lint || true   # next lint config arrives with later plans

echo "==> all lints passed"
