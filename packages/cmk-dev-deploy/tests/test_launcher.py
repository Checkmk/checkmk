# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke test for the direct launcher script (scripts/cmk-dev-deploy)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Source tree and bazel-test runfiles share this layout:
#   <root>/packages/cmk-dev-deploy/tests/test_launcher.py
#   <root>/scripts/cmk-dev-deploy.py   (data dependency of the test target)
_LAUNCHER = Path(__file__).parents[3] / "scripts" / "cmk-dev-deploy.py"


def test_launcher_prints_help() -> None:
    """The launcher finds the package from its own location and runs it."""
    result = subprocess.run(
        [sys.executable, str(_LAUNCHER), "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "usage: cmk-dev-deploy" in result.stdout
