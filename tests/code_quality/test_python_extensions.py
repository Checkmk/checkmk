#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Filesystem-level check that Python source files carry a .py extension.

Complements the Bazel aspect //bazel/tools:aspects.bzl%python_extension_checker
(backed by //packages/cmk-repo-checks), which only sees files declared in a
Bazel target's srcs. This test closes the gap for Python source files that are
not (yet) in any Bazel target.

See https://wiki.lan.checkmk.net/x/jStSCQ for the rationale and guidance on
how to fix offending files.
"""

import contextlib
import os
import subprocess
from pathlib import Path

import pytest

from cmk.repo_checks.python_extension_checker import has_python_extension_violation
from tests.code_quality.bazel_utils import git_repo_root


def _write_results_file(message: str) -> None:
    """Mirror the test summary to the file given via the RESULTS_FILE env var.

    The "Bazel sanity check" stage in the change validation passes
    RESULTS_FILE via --test_env and appends its content to the stage's
    published results file, matching the pre-Bazel implementation that still
    runs in 2.5. Outside CI the variable is unset and nothing is written.
    """
    if results_file := os.environ.get("RESULTS_FILE"):
        Path(results_file).write_text(message + "\n", encoding="utf-8")


def test_no_python_files_without_py_extension() -> None:
    """Fail if any tracked file is Python source without a .py suffix.

    Uses repo-relative paths so KNOWN_VIOLATIONS patterns anchored at the
    start of the path match as intended.
    """
    with contextlib.chdir(git_repo_root()):
        tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
        violations = [
            p
            for p in tracked
            # Skip symlinks to directories (submodule checkouts, skill trees)
            # and anything that isn't a regular file at scan time.
            if p and Path(p).is_file() and has_python_extension_violation(Path(p))
        ]
    if violations:
        message = (
            f"Found {len(violations)} Python source file(s) without a .py extension "
            "(see https://wiki.lan.checkmk.net/x/jStSCQ):\n"
            + "\n".join(f" -- {path}" for path in sorted(violations))
        )
        _write_results_file(message)
        pytest.fail(message)
    _write_results_file(f"No mismatches found in {len(tracked)} files.")
