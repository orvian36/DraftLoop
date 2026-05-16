"""RubricScorecard — maps suite metrics to the 6 rubric sections."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ScoreCell:
    title: str
    points: int
    primary_metric: str
    primary_value: Any
    threshold: Any
    status: Literal["pass", "fail"]
    note: str = ""


def _cell(
    title: str,
    points: int,
    name: str,
    value: Any,
    threshold: Any,
    *,
    lower_is_better: bool = False,
) -> ScoreCell:
    if isinstance(threshold, bool):
        status: Literal["pass", "fail"] = "pass" if value == threshold else "fail"
    elif lower_is_better:
        status = "pass" if isinstance(value, int | float) and value <= threshold else "fail"
    else:
        status = "pass" if isinstance(value, int | float) and value >= threshold else "fail"
    return ScoreCell(
        title=title,
        points=points,
        primary_metric=name,
        primary_value=value,
        threshold=threshold,
        status=status,
    )


@dataclass(frozen=True)
class RubricScorecard:
    cells: dict[str, ScoreCell]
    total_points: int = field(default=100)

    @classmethod
    def from_suite_metrics(cls, suites: dict[str, dict[str, Any]]) -> RubricScorecard:
        ing = suites.get("ingest", {})
        ret = suites.get("retrieval", {})
        dft = suites.get("drafting", {})
        imp = suites.get("improvement", {})
        cq = suites.get("code_quality", {})
        docs = suites.get("documentation", {})
        cells = {
            "doc_processing": _cell(
                "Document Processing",
                25,
                "extraction_f1",
                ing.get("extraction_f1", 0.0),
                0.90,
            ),
            "retrieval": _cell(
                "Retrieval & Grounding",
                25,
                "context_precision_at_10",
                ret.get("context_precision_at_10", 0.0),
                0.75,
            ),
            "draft_quality": _cell(
                "Draft Quality",
                10,
                "faithfulness",
                dft.get("faithfulness", 0.0),
                0.85,
            ),
            "improvement": _cell(
                "Improvement from Edits",
                25,
                "edit_distance_p50_trend_pct",
                imp.get("edit_distance_p50_trend_pct", 0.0),
                -15.0,
                lower_is_better=True,
            ),
            "code_quality": _cell(
                "Code Quality & Design",
                10,
                "coverage",
                cq.get("coverage", 0.0),
                0.80,
            ),
            "documentation": _cell(
                "Documentation & Clarity",
                5,
                "docs_lint_passed",
                docs.get("docs_lint_passed", False),
                True,
            ),
        }
        return cls(cells=cells)
