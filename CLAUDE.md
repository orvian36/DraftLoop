# DraftLoop — Contributor Contract

This file is the **modularity contract** for DraftLoop. Both human contributors
and Claude/agent contributors MUST follow it. Boundary lint, diagram lint, and
CI gates enforce most of these rules automatically; the rest are reviewer-
enforced. When in doubt, surface the conflict instead of silently relaxing it.

## 0. Read these first

Before touching code, read:

1. `docs/superpowers/specs/2026-05-15-00-overview-design.md` — system context, C4 diagrams, package layout, glossary.
2. The phase doc whose package you're working in (one of `01`..`07`).
3. This file.

If your change crosses package boundaries, also read the relevant phase doc for the consumer package.

## 1. Modularity rules (load-bearing)

1. **One public surface per package.** Each `packages/draftloop_*` exposes
   exactly one public API via its `__init__.py`. Cross-package imports MUST
   use the public surface only.
2. **No private-internal imports.** No package imports from another's
   `_internal/` submodule. Enforced by `scripts/check_boundaries.py` (Python)
   and `scripts/check_boundaries.mjs` (JS). Both run in CI.
3. **Shared types live in `draftloop_core.types`.** Anything used by ≥2
   packages MUST move there. Don't duplicate types across packages.
4. **Each package is independently testable.** `uv run pytest packages/<name>`
   passes with zero side effects from other packages.
5. **Apps are thin.** Domain logic NEVER leaks into route handlers in
   `apps/api`. Routers translate HTTP ↔ package public APIs and nothing more.
6. **`apps/` may import from `packages/`. `packages/` may NEVER import from
   `apps/`.** This is what makes packages portable to other projects.
7. **Dependency direction.** Package dependency graph is a DAG. If a new
   import would create a cycle, refactor instead of breaking the rule.

## 2. UI rules

1. `packages/ui` components are **purely presentational**:
   `(data, callbacks) → JSX`. No fetch, no API client, no API URL.
2. Data adapters and HTTP plumbing live in `apps/web/src/lib/api`.
3. Editor state lives in `packages/ui` via `zustand`. Host apps supply their
   own store factory. No global singletons.
4. Tailwind classes only. No CSS-in-JS, no styled-components, no module CSS.
5. Accessibility is required: axe-core 0-violation gate on every editor route.

## 3. Diagrams as code

1. Every architectural change MUST update its Mermaid diagram in the same PR.
2. Diagrams render via `mermaid-cli` in CI (`scripts/check_diagrams.sh`).
   Broken diagrams fail the build.
3. The diagram catalog lives in
   `docs/superpowers/specs/2026-05-15-00-overview-design.md` §7.
4. Prefer C4 (`C4Context` / `C4Container` / `C4Component` / `C4Deployment`)
   for structural views and `flowchart` / `sequenceDiagram` / `stateDiagram-v2`
   / `erDiagram` for behavioral / schema views.

## 4. LLM hygiene

1. All Gemini calls go through `draftloop_core.llm` (telemetry, retry, cost).
2. **No** direct `from google import genai` outside that module. Boundary lint
   enforces this.
3. Prompts live in `packages/<name>/prompts/*.md` — never as inline strings
   in code. Loaded with a thin loader that validates `{placeholders}` against
   a Pydantic context model.
4. Determinism in tests: `temperature=0`, fixed seeds, VCR cassettes for the
   network boundary. Tests NEVER make real Gemini calls; CI fails if one
   escapes the harness (`CostBudgetSuite`).
5. Every LLM call records: model, tokens, latency, cache hit, prompt hash,
   cost USD. These are surfaced in `audit_trail.json` for any production run.

## 5. Storage hygiene

1. Three interfaces in `draftloop_core`: `DocumentStore`, `VectorIndex`,
   `BlobStore`. Default impls: SQLite, Chroma, local FS.
2. No package opens a SQLite/Chroma file directly. Always go through the
   interface (via DI).
3. Migrations: `alembic` for the SQLite schema; one migration per PR that
   changes a table.
4. Per-matter isolation is mandatory. Every query against `VectorIndex` MUST
   filter by `matter_id`. CI grep-check fails any vector search without it.

## 6. Errors, logging, observability

1. Use `draftloop_core.errors` types. Don't raise bare `Exception`.
2. Domain errors carry a stable `code` (e.g., `INGEST_PDF_ENCRYPTED`) so the
   UI can render them without string matching.
3. `structlog` with JSON formatting in non-dev environments. Never `print`.
4. Every package's public entry point opens an OTel span named
   `<package>.<operation>`. Spans propagate via context vars.

## 7. Testing

1. New code in `packages/` requires unit tests. Coverage gate: ≥80% line.
2. Cross-package flows require an integration test under `tests/integration/`.
3. New invariants get a `hypothesis` property in the owning package.
4. UI changes require a Vitest + Testing Library test in `apps/web/tests/` or
   `packages/ui/tests/`.
5. E2E (`tests/e2e/`) is required when adding a user-visible flow.

## 8. Commits and PRs

1. Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
2. PR description includes:
   - One-line summary
   - Which phase doc the change belongs to
   - Any new architectural decisions (link the doc updated)
   - Output of `scripts/eval_diff.py prev_report.json curr_report.json` if
     the change can move an eval metric
3. New scripts in `scripts/` must accept `--help` and be idempotent.

## 9. When in doubt

- Prefer adding to `draftloop_core` over duplicating a type.
- Prefer **protocol-based** interfaces over abstract base classes.
- Prefer extending a script over adding a new one.
- If a package starts depending on >2 others, that's a smell — surface it.
- If a function grows past ~50 lines, split it.
- If a file grows past ~400 lines, that's a signal the module is doing too
  much; split by responsibility.
- If a change wants to reach across phases, document it in the phase doc
  *first*, then implement.

## 10. Anti-patterns

The following will be rejected at review:

- Direct `from google import genai` outside `draftloop_core.llm`.
- New singletons in `packages/ui`.
- Untyped JSON blobs flowing between packages (use Pydantic / TS types).
- Citation offsets stored against rendered draft text (bind by `chunk_id`).
- Style exemplars injected into fact-extraction prompts (Phase 05 anti-pattern).
- Free-form text edits with no `EditEvent` structural capture.
- Tests that hit real Gemini without `--confirm-spend`.
- Diagrams that no longer match the code they describe.

## 11. Cross-references

- Overview & glossary: `docs/superpowers/specs/2026-05-15-00-overview-design.md`
- All phase docs: `docs/superpowers/specs/2026-05-15-0{1..7}-*.md`
