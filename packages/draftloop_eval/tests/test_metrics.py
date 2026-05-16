from draftloop_eval.metrics import RubricScorecard


def test_scorecard_maps_pass_thresholds():
    sc = RubricScorecard.from_suite_metrics(
        {
            "ingest": {"extraction_f1": 0.92, "needs_review_recall": 0.85},
            "retrieval": {
                "context_precision_at_10": 0.78,
                "context_recall_at_10": 0.82,
                "hit_rate_at_5": 0.9,
            },
            "drafting": {
                "faithfulness": 0.88,
                "answer_relevance": 0.81,
                "hhem_mean": 0.78,
            },
            "improvement": {
                "edit_distance_p50_trend_pct": -20.0,
                "citation_retention_rate": 0.9,
                "anti_poison_precision": 0.96,
            },
            "code_quality": {"coverage": 0.85, "lint_clean": True},
            "documentation": {
                "docs_lint_passed": True,
                "time_to_first_draft_min": 8.0,
            },
        }
    )
    assert sc.cells["doc_processing"].status == "pass"
    assert sc.cells["retrieval"].status == "pass"
    assert sc.cells["draft_quality"].status == "pass"
    assert sc.cells["improvement"].status == "pass"
    assert sc.cells["code_quality"].status == "pass"
    assert sc.cells["documentation"].status == "pass"


def test_scorecard_marks_fail_when_below_threshold():
    sc = RubricScorecard.from_suite_metrics(
        {
            "ingest": {"extraction_f1": 0.50},
            "retrieval": {},
            "drafting": {},
            "improvement": {},
            "code_quality": {},
            "documentation": {},
        }
    )
    assert sc.cells["doc_processing"].status == "fail"
