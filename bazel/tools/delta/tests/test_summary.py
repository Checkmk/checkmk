# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from bazel_delta.files import RunCaptured
from bazel_delta.summary import changed_files, dirty_file_hashes, summary_lines

_DIRTY = ("git", "ls-files", "-z", "--modified", "--others", "--exclude-standard")


def _fake_run(dirty: str) -> RunCaptured:
    """Lists the given dirty files and hashes each path given on stdin as "h:<path>"."""

    def run(command: Sequence[str], stdin: str = "") -> str:
        if tuple(command) == _DIRTY:
            return dirty
        assert list(command) == ["git", "hash-object", "--stdin-paths"]
        return "".join(f"h:{path}\n" for path in stdin.splitlines())

    return run


def test_counts_are_right_aligned_below_the_title() -> None:
    assert summary_lines("Linting", [("Python:", 12), ("Shell (shellcheck):", 3)]) == [
        "Linting",
        "  Python:             12",
        "  Shell (shellcheck):  3",
    ]


def test_only_dirty_files_are_hashed() -> None:
    # gone.py is deleted, tests/qa-test-data a submodule and nested/ a nested repository
    run = _fake_run("a.py\0gone.py\0tests/qa-test-data\0nested/\0new.sh\0")
    files = {"a.py", "new.sh"}
    assert dirty_file_hashes(run, files.__contains__) == {"a.py": "h:a.py", "new.sh": "h:new.sh"}


def test_no_dirty_files_are_no_hashes() -> None:
    assert dirty_file_hashes(_fake_run(""), lambda _file: True) == {}


def test_changed_files_are_new_or_have_another_hash() -> None:
    before = {"same.py": "1", "fixed.py": "2"}
    after = {"same.py": "1", "fixed.py": "3", "now_dirty.py": "4"}
    assert changed_files(before, after) == ["fixed.py", "now_dirty.py"]
