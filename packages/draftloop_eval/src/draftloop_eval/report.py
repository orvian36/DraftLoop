"""Emit eval reports as JSON + Markdown + HTML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MD_TPL = """# DraftLoop Eval Report — {date}

## Rubric Scorecard

| Section | Points | Primary metric | Value | Threshold | Status |
|---|---|---|---|---|---|
{rows}

## Suites

{suites}
"""


def write_json(path: Path, suites: dict[str, Any], scorecard_summary: dict[str, Any]) -> None:
    path.write_text(
        json.dumps({"suites": suites, "scorecard": scorecard_summary}, indent=2, default=str),
        encoding="utf-8",
    )


def write_md(path: Path, suites: dict[str, Any], scorecard_rows: list[dict[str, Any]]) -> None:
    rows = "\n".join(
        f"| {r['title']} | {r['points']} | {r['primary_metric']} | {r['primary_value']} | {r['threshold']} | {r['status'].upper()} |"
        for r in scorecard_rows
    )
    suite_blocks = "\n\n".join(
        f"### {name}\n```json\n{json.dumps(metrics, indent=2, default=str)}\n```"
        for name, metrics in suites.items()
    )
    path.write_text(
        MD_TPL.format(date=path.parent.name, rows=rows, suites=suite_blocks),
        encoding="utf-8",
    )


def write_html(path: Path, suites: dict[str, Any], scorecard_rows: list[dict[str, Any]]) -> None:
    rows_html = "".join(
        f"<tr><td>{r['title']}</td><td>{r['points']}</td><td>{r['primary_metric']}</td>"
        f"<td>{r['primary_value']}</td><td>{r['threshold']}</td>"
        f"<td style='background:{'#dcfce7' if r['status'] == 'pass' else '#fee2e2'}'>{r['status'].upper()}</td></tr>"
        for r in scorecard_rows
    )
    suite_blocks = "".join(
        f"<h3>{name}</h3><pre>{json.dumps(metrics, indent=2, default=str)}</pre>"
        for name, metrics in suites.items()
    )
    html = (
        "<!DOCTYPE html>\n"
        '<html><head><meta charset="utf-8"><title>DraftLoop Eval Report</title>\n'
        "<style>body{font-family:system-ui;padding:24px;max-width:1100px;margin:auto;}"
        "table{border-collapse:collapse;width:100%;margin-bottom:24px;}"
        "td,th{border:1px solid #cbd5e1;padding:8px;text-align:left;}"
        "pre{background:#f8fafc;padding:12px;border-radius:6px;overflow-x:auto;}"
        "</style></head><body>\n"
        "<h1>DraftLoop Eval Report</h1>\n"
        "<h2>Rubric Scorecard</h2>\n"
        "<table><thead><tr><th>Section</th><th>Pts</th><th>Metric</th>"
        "<th>Value</th><th>Threshold</th><th>Status</th></tr></thead>\n"
        f"<tbody>{rows_html}</tbody></table>\n"
        f"<h2>Suites</h2>{suite_blocks}\n"
        "</body></html>\n"
    )
    path.write_text(html, encoding="utf-8")
