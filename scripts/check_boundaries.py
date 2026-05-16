#!/usr/bin/env python3
"""Boundary lint for DraftLoop packages.

Rules:
  1. No package imports from another package's `_internal/` submodule.
  2. No package imports from `apps/`.
  3. Only `draftloop_core/llm.py` may `from google import genai`.
  4. Inline escape: a line with comment `# boundary: allow <reason>` is exempt.
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path


def is_allowed_genai_module(module_path: Path) -> bool:
    parts = module_path.parts
    return "draftloop_core" in parts and module_path.name == "llm.py"


def _import_targets(node: ast.AST) -> list[tuple[str, int]]:
    """Return (module_name, lineno) tuples for every import in node."""
    out: list[tuple[str, int]] = []
    if isinstance(node, ast.ImportFrom) and node.module:
        out.append((node.module, node.lineno))
    elif isinstance(node, ast.Import):
        for alias in node.names:
            out.append((alias.name, node.lineno))
    return out


def check_file(py: Path, root: Path) -> list[str]:
    violations: list[str] = []
    try:
        source = py.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return violations

    try:
        tree = ast.parse(source, filename=str(py))
    except SyntaxError:
        return violations

    lines = source.splitlines()

    def is_exempt(lineno: int) -> bool:
        idx = lineno - 1
        if 0 <= idx < len(lines):
            return "# boundary: allow" in lines[idx]
        return False

    for node in ast.walk(tree):
        for target, lineno in _import_targets(node):
            # 1. _internal imports
            if "._internal" in target or target.endswith("._internal"):
                if not is_exempt(lineno):
                    violations.append(
                        f"{py.relative_to(root)}:{lineno}: forbidden _internal import: {target}"
                    )
            # 2. apps imports
            if target.startswith("apps.") or target == "apps":
                if not is_exempt(lineno):
                    violations.append(
                        f"{py.relative_to(root)}:{lineno}: package may not import from apps: {target}"
                    )
            # 3. google.genai imports outside draftloop_core/llm.py
            is_genai = (
                target == "google.genai" or target.startswith("google.genai.") or target == "google"
            )
            if is_genai and not is_allowed_genai_module(py) and not is_exempt(lineno):
                violations.append(
                    f"{py.relative_to(root)}:{lineno}: direct google.genai import "
                    f"outside draftloop_core/llm.py: {target}"
                )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    pkg_root = root / "packages"
    if not pkg_root.exists():
        print(f"no packages/ under {root}", file=sys.stderr)
        return 0

    all_violations: list[str] = []
    for py in pkg_root.rglob("*.py"):
        py_str = str(py)
        if (".venv" in py_str) or ("__pycache__" in py_str):
            continue
        all_violations.extend(check_file(py, root))

    if all_violations:
        print("Boundary violations found:")
        for v in all_violations:
            print(f"  {v}")
        return 1

    print("Boundaries clean.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
