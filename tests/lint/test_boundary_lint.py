"""Boundary lint test: planted violations must be flagged.

Builds tmp tree fixtures and runs `scripts/check_boundaries.py --root <tmp>`,
asserting the linter exits non-zero on violations.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_legitimate_imports_pass(tmp_path):
    pkg_a = tmp_path / "packages" / "draftloop_a" / "src" / "draftloop_a"
    pkg_b = tmp_path / "packages" / "draftloop_b" / "src" / "draftloop_b"
    for d in (pkg_a, pkg_b):
        d.mkdir(parents=True)
        (d / "__init__.py").write_text("")
    (pkg_a / "__init__.py").write_text("from draftloop_b import api\n")
    (pkg_b / "api.py").write_text("")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_internal_import_fails(tmp_path):
    pkg_a = tmp_path / "packages" / "draftloop_a" / "src" / "draftloop_a"
    pkg_b = tmp_path / "packages" / "draftloop_b" / "src" / "draftloop_b" / "_internal"
    pkg_a.mkdir(parents=True)
    pkg_b.mkdir(parents=True)
    (pkg_a / "__init__.py").write_text("from draftloop_b._internal import secret\n")
    (pkg_b.parent / "__init__.py").write_text("")
    (pkg_b / "__init__.py").write_text("")
    (pkg_b / "secret.py").write_text("")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "_internal" in (result.stdout + result.stderr)


def test_direct_genai_import_outside_core_fails(tmp_path):
    pkg = tmp_path / "packages" / "draftloop_ingest" / "src" / "draftloop_ingest"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from google import genai\n")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "genai" in (result.stdout + result.stderr).lower()


def test_genai_allowed_in_core_llm(tmp_path):
    """draftloop_core/llm.py is the legal entrypoint for google.genai."""
    pkg = tmp_path / "packages" / "draftloop_core" / "src" / "draftloop_core"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "llm.py").write_text("from google import genai\n")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_boundary_allow_comment_escape(tmp_path):
    """Inline `# boundary: allow` should exempt a single import."""
    pkg = tmp_path / "packages" / "draftloop_ingest" / "src" / "draftloop_ingest"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("from google import genai  # boundary: allow demo escape\n")

    script = Path(__file__).parents[2] / "scripts" / "check_boundaries.py"
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(tmp_path)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
