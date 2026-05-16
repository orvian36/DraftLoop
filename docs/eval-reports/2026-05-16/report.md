# DraftLoop Eval Report — 2026-05-16

## Rubric Scorecard

| Section | Points | Primary metric | Value | Threshold | Status |
|---|---|---|---|---|---|
| Document Processing | 25 | extraction_f1 | 1.0 | 0.9 | PASS |
| Retrieval & Grounding | 25 | context_precision_at_10 | 1.0 | 0.75 | PASS |
| Draft Quality | 10 | faithfulness | 0.0 | 0.85 | FAIL |
| Improvement from Edits | 25 | edit_distance_p50_trend_pct | -16.0 | -15.0 | PASS |
| Code Quality & Design | 10 | coverage | 0.85 | 0.8 | PASS |
| Documentation & Clarity | 5 | docs_lint_passed | True | True | PASS |

## Suites

### ingest
```json
{
  "extraction_f1": 1.0,
  "needs_review_recall": 1.0,
  "docs_scored": 4
}
```

### retrieval
```json
{
  "context_precision_at_10": 1.0,
  "context_recall_at_10": 1.0,
  "hit_rate_at_5": 1.0,
  "qa_total": 10
}
```

### drafting
```json
{
  "faithfulness": 0.0,
  "answer_relevance": 0.0,
  "hhem_mean": 0.0,
  "abstention_precision": 1.0,
  "abstention_recall": 0.0,
  "positives": 8,
  "negatives": 2
}
```

### improvement
```json
{
  "edit_distance_p50_trend_pct": -16.0,
  "citation_retention_rate": 0.9,
  "anti_poison_precision": 0.96,
  "weeks": 1
}
```

### end_to_end
```json
{
  "time_to_first_draft_min": 8.0
}
```

### cost_budget
```json
{
  "recorded_cost_usd": 0.0,
  "budget_usd": 2.0
}
```
