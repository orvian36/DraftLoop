# DraftLoop — Phase 05: Improvement Loop (Edit Capture → Memory → Critic → Replay)

| Field         | Value                                            |
| ------------- | ------------------------------------------------ |
| Package       | `packages/draftloop_edits`                       |
| Rubric weight | §4 Improvement from Edits — **25 points**         |
| Depends on    | `draftloop_core`, consumes `EditEvent`s from `apps/api` (Phase 04) |
| Provides     | Exemplars + Principles + Critic to `draftloop_drafting` (Phase 03) |
| Status        | Approved                                         |

## 1. Goal

Turn raw `EditEvent`s into reusable signal that **measurably** improves
future drafts. "Real improvement loop, not a side-by-side version diff" is
the rubric's explicit demand.

Architecture builds directly on **PRELUDE/CIPHER** (NeurIPS 2024) — the
closest published prior art — with production patterns layered on top:
trust weighting, recency decay, fact/style retrieval separation, and held-out
replay as the primary improvement metric.

## 2. Public API

```python
# packages/draftloop_edits/src/draftloop_edits/__init__.py
from draftloop_edits.ingestor      import EditIngestor
from draftloop_edits.classifier    import EditClassifier
from draftloop_edits.rule_inducer  import RuleInducer
from draftloop_edits.memory        import EditMemoryBank
from draftloop_edits.exemplars     import ExemplarRetriever
from draftloop_edits.catalog       import RuleCatalog
from draftloop_edits.critic        import CritiqueRunner
from draftloop_edits.trust         import TrustEngine
from draftloop_edits.replay        import ReplayHarness
from draftloop_edits.types         import (
    EditEvent, ClassifiedEdit, InducedRule, Exemplar, ExemplarBundle,
    Principle, CritiqueResult, TrustScore, ReplayReport, EditClass
)
```

**Surfaces drafting consumes** (Phase 03 wires these):

- `ExemplarRetriever.recall(source_evidence_ids, slot) -> ExemplarBundle`
- `RuleCatalog.active_principles() -> list[Principle]`
- `CritiqueRunner.review(draft, principles) -> CritiqueResult`

**Surfaces ops/eval consumes** (Phases 06 + admin pages):

- `ReplayHarness.run(date_T) -> ReplayReport` — the primary improvement metric
- `RuleCatalog.snapshot()` — operator-readable principles list

## 3. End-to-end edit lifecycle

```mermaid
flowchart TD
  A[POST /edits from apps/web] --> B[EditIngestor: validate, persist raw to SQLite]
  B --> C[Enqueue async job per EditEvent]
  C --> D[EditClassifier]
  D -- deterministic match --> E[Tag edit_class array]
  D -- fallthrough --> F[Flash 6-label classifier]
  F --> E
  E --> G{Should induce a rule?}
  G -- yes fact_correction, citation_fix, tone, structure --> H[RuleInducer: Flash 1-2 sentence rule]
  G -- no addition/deletion-only --> I[Skip induction]
  H --> J[Compute embeddings: rule_vec + source_evidence_vec]
  J --> K[EditMemoryBank.upsert]
  K --> L[TrustEngine: update operator stats]
  L --> M{Nightly batch}
  M --> N[Cluster rules to Principles]
  N --> O[RuleCatalog.publish_snapshot]
  M --> P[ReplayHarness: regen drafts T-7d -> score]
  P --> Q[Persist ReplayReport, surface /admin/replay]
  K --> R[Available for next draft via ExemplarRetriever]
  O --> S[Available for next CritiqueRunner pass]
```

## 4. `EditClassifier` — hybrid, cheapest-first

```python
class EditClass(StrEnum):
    fact_correction = "fact_correction"
    citation_fix    = "citation_fix"
    tone            = "tone"
    structure       = "structure"
    addition        = "addition"
    deletion        = "deletion"
```

**Stage A — deterministic.** Pure-Python rules, covers ~80% of edits:

| Heuristic | Label |
|---|---|
| Date / number / proper-noun regex changed in text | `fact_correction` |
| Only `Citation` list differs (no text change) | `citation_fix` |
| Whitespace / punctuation / case-only change | `tone` |
| Sentence reorder without token-set change | `structure` |
| `op == "fact_added"` | `addition` |
| `op in {"fact_deleted", "fact_marked_unsupported"}` | `deletion` |

**Stage B — Flash fallback.** Anything Stage A didn't tag (or tagged
ambiguously) → `gemini-2.5-flash` with a 6-label classification prompt and
per-label confidence. Multi-label allowed.

## 5. `RuleInducer` — induced-rule per edit

For each classified edit (except pure `addition`/`deletion`), Flash produces
a **1–2 sentence portable rule**:

```
INPUT:
  before: "Plaintiff alleges breach of contract on March 14th, 2024."
  after:  "Plaintiff alleges breach of the SaaS agreement on 2024-03-14."
  source_evidence: [chunk doc_3_p4_¶12: "...the SaaS agreement, executed 2024-03-14..."]
  edit_class: [fact_correction, tone]
OUTPUT (induced_rule):
  "Use ISO-8601 dates and specify the contract type (e.g., 'SaaS agreement')
   rather than generic 'contract' when source identifies it."
```

The induced rule is the **embedding payload** that makes retrieval-of-edits
useful at draft time. Embedded with `gemini-embedding-001`
(`task_type=RETRIEVAL_DOCUMENT`).

## 6. `EditMemoryBank` — dual-vector

```mermaid
flowchart LR
  A[ClassifiedEdit + InducedRule] --> B[Embed induced_rule -> rule_vec 1536d]
  A --> C[Concat source_evidence chunks -> embed -> evidence_vec 1536d]
  B --> D[Chroma: edit_memory_rule]
  C --> E[Chroma: edit_memory_evidence]
  D --> F["metadata: edit_id, class_labels, operator_id, ts, trust_weight, slot"]
  E --> F
```

Two separate collections so we can query by **rule similarity** and **evidence
similarity** independently. Hits fused via RRF.

## 7. `ExemplarRetriever` — fact-pass and style-pass

Two **independent** retrievals so style exemplars never contaminate fact
extraction (research-validated anti-pattern).

```python
class Exemplar(BaseModel):
    edit_id: str
    induced_rule: str
    before_text: str | None
    after_text: str | None
    edit_class: list[EditClass]
    operator_id: str
    trust_weight: float
    age_days: int

class ExemplarBundle(BaseModel):
    fact_exemplars: list[Exemplar]    # max 5
    style_exemplars: list[Exemplar]   # max 3
    total_tokens: int                 # hard cap 2,000
```

Per pass:

```mermaid
flowchart TD
  Q[Query: source_evidence_ids + slot] --> A[evidence_vec via mean-pooled chunk embeddings]
  Q --> B[rule_intent embedding: 'rules about <slot>']
  A --> C[Chroma evidence_collection top-20]
  B --> D[Chroma rule_collection top-20]
  C --> E[RRF fuse]
  D --> E
  E --> F[Filter: edit_class subset matches pass type]
  F --> G[Score = base_rrf * trust_weight * exp -age_days/30]
  G --> H[Diversify: cap 2 per operator out of top-k]
  H --> I[Token-budget trim: drop until total_tokens <= 2,000]
  I --> J[Return Exemplar list]
```

**Fact pass** filters to `{fact_correction, citation_fix}`, k=5.
**Style pass** filters to `{tone, structure}`, k=3.

## 8. `RuleCatalog` — Constitutional Principles

Nightly batch job:

1. Pull `induced_rule`s with `trust_weight ≥ 0.5`, last 90 days.
2. Embed; cluster via HDBSCAN (no fixed k — emergent groupings).
3. Per cluster of ≥3 rules → Flash summarizes into a **Principle** (≤30 words,
   imperative voice).
4. Hand-review queue at `/admin/rules`: approve / reject / edit.
5. Approved Principles are the `style_rules` block for drafting and the
   `principles` input to `CritiqueRunner`.

Hard cap: **≤50 active Principles**. Excess demoted by coverage.

## 9. `CritiqueRunner` — pre-ship critic

```mermaid
sequenceDiagram
  participant D as draftloop_drafting
  participant C as CritiqueRunner
  participant F as Gemini Flash
  participant R as RuleCatalog

  D->>C: review(draft, source_chunks)
  C->>R: active_principles()
  R-->>C: list[Principle]
  C->>F: per Fact - is each Citation supported? does Fact violate any Principle?
  F-->>C: per-fact {supported, violations[], suggested_rewrite?}
  C-->>D: CritiqueResult (advisory by default)
```

- Advisory by default — never mutates `Fact`s.
- `CRITIC_AUTO_APPLY=true` enables auto-apply of deterministic rewrites only
  (date format normalization, term substitution) and never touches citations.
- Uses Flash (cheap); ~1–2s end-to-end latency.

## 10. `TrustEngine` — defend against catastrophic feedback

| Mechanism | What it does |
|---|---|
| Pairwise agreement | Two operators editing the same slot across matters → Jaccard score → below-median operators get `trust_weight=0.5` |
| Reversion demotion | Operator B undoes A's edit within 7 days → A's `trust_weight *= 0.3`; after 14 days A's edit excluded from new retrievals |
| Per-operator cap | `ExemplarRetriever` caps any single operator to ≤2 of top-5 / ≤1 of top-3 |
| Recency decay | `score *= exp(-age_days / 30)`; hard cutoff at 180 days unless re-affirmed |
| Approval pin | Operator can pin an edit ("house style") → `trust_weight=1.0`, decay-exempt |
| Seed rules | Bootstrap with 5–10 curated rules under `operator_id="__seed__"` so cold-start works |

## 11. `ReplayHarness` — primary improvement metric

```mermaid
sequenceDiagram
  participant H as ReplayHarness
  participant DB as SQLite
  participant D as Drafter (sandbox)
  participant M as MemoryBank (frozen view)

  H->>DB: load matters with approved_final_draft and edit_history >= T
  loop per matter
    H->>M: freeze view at T - 7d (only edits before T-7d visible)
    H->>D: draft(matter, exemplars_from(M_frozen))
    D-->>H: candidate_draft
    H->>H: compare candidate vs operator_final
  end
  H->>DB: persist ReplayReport
```

**Reported metrics:**

- `edit_distance_per_draft` (lower-is-better) — primary trendline
- `citation_retention_rate`
- `fact_jaccard_high_confidence`
- `unsupported_rate_delta` (correct abstention behavior)
- `time_to_approve_s_p50` (pulled from production sessions, separate input)

Surfaced at `/admin/replay`. This chart is what the README leads with.

## 12. Component-level C4

```mermaid
C4Component
  title draftloop_edits — Components
  Container_Boundary(edits, "draftloop_edits") {
    Component(ingest,   "EditIngestor",      "Python", "Validate + persist raw EditEvent")
    Component(classify, "EditClassifier",    "Python", "Deterministic + Flash 6-label hybrid")
    Component(induce,   "RuleInducer",       "Python", "Flash 1-2 sentence rule")
    Component(memory,   "EditMemoryBank",    "Python", "Dual-vector Chroma collections")
    Component(retr,     "ExemplarRetriever", "Python", "Fact-pass + style-pass with trust/recency")
    Component(catalog,  "RuleCatalog",       "Python", "Nightly cluster -> Principles")
    Component(critic,   "CritiqueRunner",    "Python", "Advisory pre-ship critic")
    Component(trust,    "TrustEngine",       "Python", "Agreement, reversion, decay, pin")
    Component(replay,   "ReplayHarness",     "Python", "Held-out CIPHER-style regen + scoring")
  }
  ContainerDb(sqlite, "SQLite",  "edit_events, classifications, rules, principles, trust, replay_reports")
  ContainerDb(chroma, "Chroma",  "edit_memory_rule, edit_memory_evidence")
  Container_Ext(drafting, "draftloop_drafting")
  System_Ext(gemini,  "Gemini Flash + Embedding")

  Rel(ingest, sqlite, "insert raw")
  Rel(classify, gemini, "Flash fallback")
  Rel(classify, sqlite, "update class")
  Rel(induce, gemini, "Flash")
  Rel(induce, memory, "upsert rule")
  Rel(memory, chroma, "embed + upsert")
  Rel(retr, chroma, "search dual-vector")
  Rel(retr, trust, "weights")
  Rel(catalog, sqlite, "read induced_rules; write principles")
  Rel(catalog, gemini, "Flash cluster summarize")
  Rel(critic, catalog, "active principles")
  Rel(critic, gemini, "Flash review")
  Rel(replay, drafting, "regen drafts")
  Rel(replay, memory, "frozen view")
  Rel(drafting, retr, "recall(...)")
  Rel(drafting, critic, "review(...)")
```

## 13. ER schema (additions for this phase)

```mermaid
erDiagram
  EDIT_EVENT ||--o{ CLASSIFIED_EDIT : "classified as"
  CLASSIFIED_EDIT ||--o| INDUCED_RULE : "induces"
  INDUCED_RULE }o--|| PRINCIPLE : "clustered into"
  OPERATOR ||--o{ EDIT_EVENT : "authors"
  OPERATOR ||--|| TRUST_SCORE : "current"
  DRAFT ||--o{ EDIT_EVENT : "amended by"
  REPLAY_REPORT ||--o{ DRAFT : "scores"

  EDIT_EVENT {
    string event_id PK
    string draft_id
    string matter_id
    string slot
    string sentence_id
    string op
    varchar before
    varchar after
    varchar source_evidence_ids
    string word_diff
    int time_to_edit_ms
    string operator_id
    string draft_model_version
    string prompt_hash
    datetime timestamp
  }
  CLASSIFIED_EDIT {
    string event_id PK
    varchar edit_class_labels
    varchar classifier_confidences
    string classifier_version
    datetime classified_at
  }
  INDUCED_RULE {
    string rule_id PK
    string event_id FK
    string rule_text
    string rule_vec_chroma_id
    string evidence_vec_chroma_id
    float trust_weight
    bool pinned
    datetime created_at
  }
  PRINCIPLE {
    string principle_id PK
    string principle_text
    varchar source_rule_ids
    string status "active|proposed|retired"
    int coverage_count
    datetime approved_at
    string approved_by
  }
  TRUST_SCORE {
    string operator_id PK
    float agreement_score
    int reversions_against
    int reversions_caused
    float current_weight
    datetime updated_at
  }
  REPLAY_REPORT {
    string report_id PK
    date week_ending
    int matters_replayed
    float edit_distance_p50
    float citation_retention_rate
    float fact_jaccard_p50
    float unsupported_rate
    varchar per_matter
    datetime generated_at
  }
```

## 14. Tests

| Layer | Coverage |
|---|---|
| Classifier unit | Golden `(before, after)` pairs per `EditClass` → assert Stage A correctness; Stage B confident picks |
| RuleInducer integration | Curated 10-pair set → induced rules snapshot test for stability |
| MemoryBank | Upsert idempotency on `edit_id`; deletion cascades; per-matter isolation |
| ExemplarRetriever | Synthetic edit corpus → (a) token budget honored, (b) per-operator cap honored, (c) fact-pass returns zero `tone`/`structure` exemplars and vice versa |
| TrustEngine | Scripted reversion sequence → assert demotion math; pinned edits exempt |
| CritiqueRunner | Drafts with planted Principle violations → critic flags them |
| ReplayHarness e2e | 5 matters × 3 weeks of edits → assert `edit_distance` improves on "good" stream, flat on noisy control |
| Anti-poisoning | 1 operator with bad edits → trust < 0.5 within N reversions; exemplars filtered out |

## 15. Failure modes & mitigation

| Failure | Mitigation |
|---|---|
| Paste-bomb (10k tiny edits / sec) | Per-operator rate limit at ingest; consecutive edits on same Fact within 10s auto-batched |
| Flash classifier hallucinates a label | Schema enforces enum; OOV → Stage A only, flagged for review |
| Induced rule contradicts existing Principle | Catalog clustering surfaces as `conflict` item at `/admin/rules` |
| Memory bank grows unbounded | TTL 180 days unless pinned; nightly compaction |
| Replay hits Gemini rate limits | Batch API; overnight runs with no SLA |
| Cold start: no edits yet | `ExemplarRetriever` returns empty bundle; drafting skips exemplar block — no errors |
| All operators bad → no anchor | Bootstrap 5–10 pinned `__seed__` rules; replaceable as real signal accumulates |
| Critic suggests rewrite that violates another Principle | Single-pass advisory; no auto-rewrite loop |
| Reverted-edit detection false-positive (legit re-edit of same wording) | Reversion demotion is soft (`*=0.3`, not zero); a single FP is recoverable |

## 16. Open decisions deferred to implementation

- Async job runner: FastAPI `BackgroundTasks` (Phase 07 default) vs lightweight in-process queue. Both honor the public API.
- Nightly job scheduler: `apscheduler` in the API process vs cron container. Proposed: `apscheduler` (one process to run).
- Principle hand-review UI: minimal table at `/admin/rules` for v1; richer batch operations later.

## 17. Cross-references

- Overview: `2026-05-15-00-overview-design.md`
- Consumer (drafting): `2026-05-15-03-drafting-design.md`
- Producer (UI/edit capture): `2026-05-15-04-operator-ui-design.md`
- Eval that calls `ReplayHarness`: `2026-05-15-06-evaluation-design.md`
