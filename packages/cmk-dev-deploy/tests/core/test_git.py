# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.core.git (shared git queries)."""

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from cmk.dev_deploy.core.git import query_untracked_files

_RUN = "cmk.dev_deploy.core.git.subprocess.run"

REPO = Path("/fake/repo")


def _mock_run(
    returncode: int = 0,
    stdout: str = "",
) -> object:
    """Create a callable returning a fixed CompletedProcess."""

    def _run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=cmd, returncode=returncode, stdout=stdout, stderr=""
        )

    return _run


class TestGetUntrackedFiles:
    """Tests for query_untracked_files()."""

    def test_parses_paths(self) -> None:
        """Splits stdout into paths and drops blank lines."""
        with patch(_RUN, _mock_run(stdout="a/new.vue\n\nb/new.py\n")):
            assert query_untracked_files(REPO) == ["a/new.vue", "b/new.py"]

    def test_empty_output(self) -> None:
        """No untracked files yields an empty list."""
        with patch(_RUN, _mock_run(stdout="")):
            assert query_untracked_files(REPO) == []

    def test_excludes_gitignored_files(self) -> None:
        """Passes --exclude-standard so build output stays out of the diff.

        Without it every Bazel symlink and editor scratch file would enter
        change detection and force a rebuild on every run.
        """
        captured: list[list[str]] = []

        def _capture(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            captured.append(cmd)
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

        with patch(_RUN, _capture):
            query_untracked_files(REPO)

        assert captured == [["git", "ls-files", "--others", "--exclude-standard"]]

    def test_nonzero_exit_returns_empty(self) -> None:
        """A git failure degrades to tracked-only detection, not a crash."""
        with patch(_RUN, _mock_run(returncode=128)):
            assert query_untracked_files(REPO) == []

    @pytest.mark.parametrize(
        "exc",
        [subprocess.TimeoutExpired(cmd="git", timeout=5), OSError("no git")],
    )
    def test_subprocess_errors_return_empty(self, exc: Exception) -> None:
        """Timeouts and a missing git binary are non-fatal."""
        with patch(_RUN, side_effect=exc):
            assert query_untracked_files(REPO) == []
