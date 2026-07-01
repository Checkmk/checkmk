#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests requiring git access — run with ``tags=["local"]`` (no Bazel sandbox)."""

import os
import subprocess
from pathlib import Path

from cmk.utils.werks.__main__ import main as cmk_utils_werks_main
from cmk.werks.tool.cli import main as cmk_werks_cli_main
from cmk.werks.tool.utils.__main__ import main as cmk_werks_main

# How far back `test_mail` walks, counted in commits that touch a werk rather than
# in time: a time window can contain no werk at all (CMK-33663).
_MAILED_WERK_COMMITS = 20


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
    """Smoke test for `//cmk/utils:werks_bin -- mail`: mails the last werk changes."""
    repo_root = _git_repo_root()
    werk_commits = subprocess.check_output(
        ["git", "log", f"-{_MAILED_WERK_COMMITS}", "--format=%H", "--", ".werks/[0-9]*"],
        cwd=repo_root,
        text=True,
    ).split()
    assert werk_commits, "found no commit touching a werk — incomplete checkout?"
    assume_no_notes_but = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{werk_commits[-1]}^"],
        cwd=repo_root,
        text=True,
    ).strip()

    cmk_utils_werks_main(
        [
            "mail",
            str(repo_root),
            "HEAD",
            "werk_mail",
            f"--assume-no-notes-but={assume_no_notes_but}",
        ]
    )
