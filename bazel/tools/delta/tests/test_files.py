# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest
from bazel_delta.errors import DeltaError
from bazel_delta.files import (
    delta_files,
    existing_files,
    FileStatus,
    find_base_branch,
    RunCaptured,
)

_MERGE_BASE = ("git", "merge-base", "HEAD", "origin/master")
_DIFF = ("git", "diff", "-z", "--name-status", "--no-renames", "--ignore-submodules", "abc123")
_UNTRACKED = ("git", "ls-files", "-z", "--others", "--exclude-standard")


def _make(name: str) -> tuple[str, ...]:
    return ("make", "--no-print-directory", "-f", "defines.make", f"print-{name}")


def _fake_run(outputs: Mapping[tuple[str, ...], str]) -> RunCaptured:
    """Returns the output given for a command, fails for any other command."""

    def run(command: Sequence[str]) -> str:
        if (output := outputs.get(tuple(command))) is None:
            raise DeltaError(f"{' '.join(command)} failed")
        return output

    return run


def test_master_compares_with_origin_master() -> None:
    run = _fake_run({_make("BRANCH_NAME_IS_BRANCH_VERSION"): "\n"})
    assert find_base_branch(run) == "origin/master"


def test_stable_branch_compares_with_its_version() -> None:
    run = _fake_run(
        {_make("BRANCH_NAME_IS_BRANCH_VERSION"): "yes\n", _make("BRANCH_VERSION"): "3.0.0\n"}
    )
    assert find_base_branch(run) == "origin/3.0.0"


def test_files_have_their_git_status() -> None:
    run = _fake_run(
        {
            _MERGE_BASE: "abc123\n",
            _DIFF: "M\0cmk/a.py\0A\0with space.md\0D\0cmk/old.py\0T\0link\0",
            _UNTRACKED: "new.sh\0",
        }
    )
    assert delta_files(run, "origin/master") == {
        "cmk/a.py": FileStatus.MODIFIED,
        "with space.md": FileStatus.ADDED,
        "cmk/old.py": FileStatus.DELETED,
        "link": FileStatus.MODIFIED,
        "new.sh": FileStatus.UNTRACKED,
    }


def test_untracked_nested_repositories_are_no_files() -> None:
    run = _fake_run({_MERGE_BASE: "abc123\n", _DIFF: "", _UNTRACKED: "nested/\0new.sh\0"})
    assert delta_files(run, "origin/master") == {"new.sh": FileStatus.UNTRACKED}


def test_no_changes_are_no_files() -> None:
    run = _fake_run({_MERGE_BASE: "abc123\n", _DIFF: "", _UNTRACKED: ""})
    assert delta_files(run, "origin/master") == {}


def test_existing_files_leave_out_the_deleted_ones() -> None:
    files = {
        "a.py": FileStatus.MODIFIED,
        "old.py": FileStatus.DELETED,
        "n.sh": FileStatus.UNTRACKED,
    }
    assert existing_files(files) == ["a.py", "n.sh"]


def test_missing_base_branch_is_an_error() -> None:
    with pytest.raises(DeltaError, match="cannot compare with origin/master, does it exist"):
        delta_files(_fake_run({}), "origin/master")
