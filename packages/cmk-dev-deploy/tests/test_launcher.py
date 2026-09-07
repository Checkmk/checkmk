# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke tests for the launcher script (scripts/cmk-dev-deploy.py).

The launcher runs the tool on the checkout's ``.venv``, which the Bazel
sandbox does not have.  Each test therefore stages a minimal checkout: the
launcher under ``scripts/``, the package under ``packages/``, and a ``.venv``
whose ``python3`` is the test interpreter.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# Source tree and bazel-test runfiles share this layout:
#   <root>/packages/cmk-dev-deploy/tests/test_launcher.py
#   <root>/scripts/cmk-dev-deploy.py   (data dependency of the test target)
_LAUNCHER = Path(__file__).parents[3] / "scripts" / "cmk-dev-deploy.py"
_PACKAGE_DIR = Path(__file__).parents[1]


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    (tmp_path / "scripts").mkdir()
    shutil.copy(_LAUNCHER, tmp_path / "scripts" / "cmk-dev-deploy.py")
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages" / "cmk-dev-deploy").symlink_to(_PACKAGE_DIR)
    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    (venv_bin / "python3").symlink_to(sys.executable)
    return tmp_path


def _run_launcher(checkout: Path, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(checkout / "scripts" / "cmk-dev-deploy.py"), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        cwd=cwd,
    )


def test_launcher_hands_over_to_the_venv_interpreter(checkout: Path) -> None:
    fake_python = checkout / ".venv" / "bin" / "python3"
    fake_python.unlink()
    fake_python.write_text('#!/bin/sh\necho "fake venv python $*"\n')
    fake_python.chmod(0o755)

    result = _run_launcher(checkout, "--help", cwd=checkout)

    launcher = (checkout / "scripts" / "cmk-dev-deploy.py").resolve()
    assert result.stdout.strip() == f"fake venv python {launcher} --help"


def test_launcher_runs_the_tool_on_the_venv_interpreter(checkout: Path) -> None:
    result = _run_launcher(checkout, "--help", cwd=checkout)

    assert result.returncode == 0, result.stderr
    assert "usage: cmk-dev-deploy" in result.stdout


def test_launcher_is_independent_of_the_working_directory(checkout: Path) -> None:
    result = _run_launcher(checkout, "--help", cwd=Path("/"))

    assert result.returncode == 0, result.stderr
    assert "usage: cmk-dev-deploy" in result.stdout


def test_launcher_refuses_to_run_without_the_venv(checkout: Path) -> None:
    shutil.rmtree(checkout / ".venv")

    result = _run_launcher(checkout, "--help", cwd=checkout)

    assert result.returncode == 1
    assert "make .venv" in result.stderr
