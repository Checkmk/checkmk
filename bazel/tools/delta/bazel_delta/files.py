# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The files a --delta option covers."""

import subprocess
from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path

from bazel_delta.errors import DeltaError

# Runs a command in the workspace and returns its stdout, raises DeltaError if it fails.
type RunCaptured = Callable[[Sequence[str]], str]


def run_captured_in(workspace: Path) -> RunCaptured:
    def run(command: Sequence[str]) -> str:
        try:
            return subprocess.run(
                command,
                cwd=workspace,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as e:
            raise DeltaError(f"{' '.join(command)} failed: {getattr(e, 'stderr', e)}") from e

    return run


def _make_variable(run: RunCaptured, name: str) -> str:
    return run(["make", "--no-print-directory", "-f", "defines.make", f"print-{name}"]).strip()


def find_base_branch(run: RunCaptured) -> str:
    """origin/<BRANCH_VERSION> on a stable branch, else origin/master."""
    if _make_variable(run, "BRANCH_NAME_IS_BRANCH_VERSION"):
        return f"origin/{_make_variable(run, 'BRANCH_VERSION')}"
    return "origin/master"


class FileStatus(StrEnum):
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNTRACKED = "untracked"


# The letters of `git diff --name-status`; anything else, e.g. a type change, is a modification
_GIT_STATUS = {"A": FileStatus.ADDED, "D": FileStatus.DELETED}


def delta_files(run: RunCaptured, base_branch: str) -> dict[str, FileStatus]:
    """Every file that differs from the merge-base, with how it changed: committed,
    staged, unstaged or untracked. A rename counts as the deletion of the old path
    and the addition of the new one."""
    try:
        merge_base = run(["git", "merge-base", "HEAD", base_branch]).strip()
    except DeltaError as e:
        raise DeltaError(f"cannot compare with {base_branch}, does it exist?") from e
    # Pairs of status letter and path, each terminated by a NUL byte
    changed = run(
        [
            "git",
            "diff",
            "-z",
            "--name-status",
            "--no-renames",
            "--ignore-submodules",
            merge_base,
        ]
    ).split("\0")
    files = {
        path: _GIT_STATUS.get(status, FileStatus.MODIFIED)
        for status, path in zip(changed[0::2], changed[1::2])
        if path
    }
    untracked = run(["git", "ls-files", "-z", "--others", "--exclude-standard"])
    # Untracked nested repositories are listed as "<dir>/"
    files.update(
        (file, FileStatus.UNTRACKED)
        for file in untracked.split("\0")
        if file and not file.endswith("/")
    )
    return files


def existing_files(files: Mapping[str, FileStatus]) -> list[str]:
    """The files that were not deleted."""
    return [file for file, status in files.items() if status is not FileStatus.DELETED]
