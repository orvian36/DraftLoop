"""CLI entrypoint: python -m draftloop_eval --manifest <path> --out <dir>"""

from __future__ import annotations

import argparse
from pathlib import Path

from draftloop_eval.report import write_html, write_json, write_md
from draftloop_eval.runner import EvalRunner


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/golden/manifest.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--suite", default=None, help="Run only the named suite")
    parser.add_argument("--offline", action="store_true", help="Skip suites needing Gemini")
    args = parser.parse_args()

    runner = EvalRunner(
        manifest_path=Path(args.manifest),
        pdf_root=Path("data/synthetic"),
    )
    report = runner.run(suites=[args.suite] if args.suite else None)

    rows = [
        {
            "title": c.title,
            "points": c.points,
            "primary_metric": c.primary_metric,
            "primary_value": c.primary_value,
            "threshold": c.threshold,
            "status": c.status,
        }
        for c in report.scorecard.cells.values()
    ]

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "metrics.json", report.suites, {"rows": rows})
    write_md(out_dir / "report.md", report.suites, rows)
    write_html(out_dir / "report.html", report.suites, rows)
    print(f"==> wrote {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
