# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Smoke tests for the launcher scripts/cmk-dev-site.py and its symlinks.

The launcher runs the commands on the checkout's ``.venv``, which the Bazel
sandbox does not have. Each test therefore stages a minimal checkout: the
launcher and its symlinks under ``scripts/``, a stub ``cmk_dev_site`` under
``packages/cmk-dev`` whose commands print their name, and a ``.venv`` whose
``python3`` runs the test interpreter. The test interpreter can import the
real ``cmk_dev_site`` too, so seeing a stub's output proves that the
launcher prefers the checkout's package.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).parents[3] / "scripts"
_COMMANDS = {
    "cmk-dev-site": ("cmk_dev_site/cmk_dev_site.py", "main"),
    "cmk-dev-install": ("cmk_dev_site/cmk_dev_install.py", "main"),
    "cmk-dev-install-site": ("cmk_dev_site/cmk_dev_install_site.py", "main"),
    "cmk-dev-site-mock-auth": ("cmk_dev_site/saas/oidc_service.py", "run"),
}


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    shutil.copy(_SCRIPTS_DIR / "cmk-dev-site.py", scripts / "cmk-dev-site.py")
    for command in _COMMANDS:
        if command != "cmk-dev-site":
            (scripts / f"{command}.py").symlink_to("cmk-dev-site.py")

    package = tmp_path / "packages" / "cmk-dev"
    for command, (module, function) in _COMMANDS.items():
        path = package / module
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.parent / "__init__.py").touch()
        path.write_text(f"def {function}() -> None:\n    print('stub {command}')\n")

    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    # A wrapper, not a symlink: a symlinked interpreter would look for its venv
    # next to the link and miss the test's third-party packages.
    python = venv_bin / "python3"
    python.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    python.chmod(0o755)
    return tmp_path


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("command", _COMMANDS)
def test_every_wheel_command_name_runs_the_launcher(command: str) -> None:
    launcher = (_SCRIPTS_DIR / "cmk-dev-site.py").read_bytes()

    assert (_SCRIPTS_DIR / f"{command}.py").read_bytes() == launcher


@pytest.mark.parametrize("command", _COMMANDS)
def test_started_name_runs_that_command_from_the_checkout(checkout: Path, command: str) -> None:
    result = _run(checkout / "scripts" / f"{command}.py", "--version")

    assert result.returncode == 0, result.stderr
    assert result.stdout == f"stub {command}\n"


def test_unknown_name_is_rejected(checkout: Path) -> None:
    (checkout / "scripts" / "cmk-dev-other.py").symlink_to("cmk-dev-site.py")

    result = _run(checkout / "scripts" / "cmk-dev-other.py")

    assert result.returncode == 1
    assert "unknown command name" in result.stderr


def test_missing_venv_tells_how_to_create_it(checkout: Path) -> None:
    shutil.rmtree(checkout / ".venv")

    result = _run(checkout / "scripts" / "cmk-dev-install.py", "--version")

    assert result.returncode == 1
    assert "make .venv" in result.stderr
