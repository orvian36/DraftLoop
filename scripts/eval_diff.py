#!/usr/bin/env python3
"""Diff two eval reports' metrics.json files."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: eval_diff.py prev.json curr.json", file=sys.stderr)
        return 2
    prev = json.loads(Path(sys.argv[1]).read_text())
    curr = json.loads(Path(sys.argv[2]).read_text())
    keys = sorted(set(prev["suites"]) | set(curr["suites"]))
    diffs = 0
    for k in keys:
        before = prev["suites"].get(k, {})
        after = curr["suites"].get(k, {})
        for m_key in sorted(set(before) | set(after)):
            b = before.get(m_key)
            a = after.get(m_key)
            if b == a:
                continue
            print(f"  {k}.{m_key}: {b} -> {a}")
            diffs += 1
    if diffs == 0:
        print("(no metric changes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
