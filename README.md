# DraftLoop

Ingest messy legal documents → generate **grounded** drafts → improve from operator edits.

## Quick start

```bash
git clone <repo>
cd DraftLoop
cp .env.example .env       # add your GEMINI_API_KEY
bash scripts/setup.sh
bash scripts/dev.sh
# open http://localhost:3000
```

## What's here right now (Plan 0)

- Turborepo monorepo: uv (Python) + pnpm (JS) workspaces, orchestrated by Turbo.
- `packages/draftloop_core` — shared types, errors, config, Gemini SDK shim, storage protocols, observability.
- `apps/api` — FastAPI skeleton with `/health` and `/version`.
- `apps/web` — Next.js 15 + Tailwind landing page that pings the API.
- `packages/ui` — first shared React component (`HealthBadge`), shipped via tsup.
- Boundary lint (`scripts/check_boundaries.py`) + diagram lint (`scripts/check_diagrams.sh`) + bundled `scripts/lint.sh`.
- GitHub Actions CI: lint + Python unit tests + JS unit tests + diagram render.

## What's coming

See `docs/superpowers/plans/2026-05-15-plans-index.md` for the full sequenced roadmap. The implementation walks through Plans 1–7 (ingestion → retrieval → drafting → operator UI → improvement loop → evaluation → composition + demo).

## Reading order

1. `docs/superpowers/specs/2026-05-15-00-overview-design.md` — system context, C4 diagrams, glossary.
2. The phase doc whose package you're touching (`01`..`07`).
3. `CLAUDE.md` — contributor / modularity contract.

## Commands

| Command | Purpose |
|---|---|
| `bash scripts/setup.sh` | One-shot environment bring-up |
| `bash scripts/dev.sh` | Boot API + web together |
| `bash scripts/lint.sh` | Run every lint gate locally |
| `uv run pytest` | Python tests |
| `pnpm -r test` | JS tests |

## License

TBD.
