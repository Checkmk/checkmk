#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests requiring git access — run with ``tags=["local"]`` (no Bazel sandbox)."""

import datetime
import os
import subprocess
from pathlib import Path

import pytest

from cmk.utils.werks.__main__ import main as cmk_utils_werks_main
from cmk.werks.cli import main as cmk_werks_cli_main
from cmk.werks.utils.__main__ import main as cmk_werks_main


def _git_repo_root() -> Path:
    """Return the real git repository root (not the Bazel runfiles tree)."""
    return Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())


def test_collect() -> None:
    """Smoke test for `//packages/cmk-werks:utils-bin -- collect`."""
    # The branch name is hardcoded to master, but this is intentional —
    # it works correctly on version branches too.
    cmk_werks_main(
        ["collect", "cmk", str(_git_repo_root()), "--substitute-branches", "master:HEAD"]
    )


def test_list() -> None:
    """Smoke test for `werk list`."""
    original_cwd = os.getcwd()
    try:
        cmk_werks_cli_main(["list"])
    finally:
        # Ensure we return to the original working directory, since `werk list` changes it
        os.chdir(original_cwd)


def test_mail() -> None:
    """Smoke test for `//cmk/utils:werks_bin -- mail`."""
    four_weeks_ago = (datetime.datetime.now() - datetime.timedelta(weeks=4)).isoformat()
    assume_no_notes_but = subprocess.check_output(
        ["git", "log", f"--before={four_weeks_ago}", "--format=%H", "--max-count=1"],
        text=True,
    ).strip()
    if not assume_no_notes_but:
        pytest.skip("No commit older than 4 weeks found")

    cmk_utils_werks_main(
        [
            "mail",
            str(_git_repo_root()),
            "HEAD",
            "werk_mail",
            f"--assume-no-notes-but={assume_no_notes_but}",
        ]
    )
