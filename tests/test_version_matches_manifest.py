# =============================================================================
# URTC-GATEWAY - tests/test_version_matches_manifest.py
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0-or-later - see LICENSE
# =============================================================================
"""The version the package reports is the version of the project: the manifest, pyproject.toml and every README badge say the same."""
from __future__ import annotations

import json
import re
from pathlib import Path

from urtc_gateway import __version__

ROOT = Path(__file__).resolve().parents[1]


def test_the_package_reports_the_version_of_the_manifest():
    manifest = json.loads((ROOT / "urtc.project.json").read_text(encoding="utf-8"))
    assert __version__ == manifest["version"]


def test_pyproject_and_the_package_agree():
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.M)
    assert match is not None and match.group(1) == __version__


def test_every_readme_badge_shows_that_version():
    readmes = sorted(ROOT.glob("README*.md"))
    if not readmes:  # an installation without the documentation
        return
    assert len(readmes) == 8
    for readme in readmes:
        found = re.search(r"badge/Version-([0-9][0-9.]*)-", readme.read_text(encoding="utf-8"))
        assert found is not None and found.group(1) == __version__, readme.name
