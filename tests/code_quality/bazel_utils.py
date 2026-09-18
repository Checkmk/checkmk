#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path


def bazel_repo_root() -> Path:
    """Resolve the repo root from Bazel runfiles.

    Points into the runfiles tree: only inputs declared as srcs/data of the
    test target exist there, and there is no `.git`. Use git_repo_root()
    instead for tests that inspect the git worktree.
    """
    try:
        test_srcdir = os.environ["TEST_SRCDIR"]
        test_workspace = os.environ["TEST_WORKSPACE"]
    except KeyError as exc:
        raise RuntimeError(
            "TEST_SRCDIR and TEST_WORKSPACE must be set. This test must be run via Bazel."
        ) from exc
    return Path(test_srcdir) / test_workspace


def git_repo_root() -> Path:
    """Resolve the real checkout root (the directory containing `.git`).

    In contrast to bazel_repo_root(), this escapes the runfiles tree via
    Path.resolve() — the calling test must be tagged "no-sandbox" — and is
    the right base for tests that run git commands or read undeclared files
    from the worktree.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Could not find repository root (no .git found)")
