#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path
from typing import cast

import requirements

from tests.code_quality.bazel_utils import bazel_repo_root


def get_branch() -> str:
    """Return the current branch name.

    Checks GERRIT_BRANCH env var first (set in CI), then falls back to parsing
    defines.make: if BRANCH_NAME_IS_BRANCH_VERSION is set, the branch name equals
    BRANCH_VERSION; otherwise the branch is "master".
    """
    if gerrit_branch := os.environ.get("GERRIT_BRANCH"):
        return gerrit_branch
    # Fallback for local runs, where GERRIT_BRANCH is not set
    branch_version: str | None = None
    branch_name_is_branch_version: str | None = None
    with open(bazel_repo_root() / "defines.make") as f:
        for line in f:
            key, _, value = line.partition(":=")
            key, value = key.strip(), value.strip()
            if key == "BRANCH_VERSION":
                branch_version = value
            elif key == "BRANCH_NAME_IS_BRANCH_VERSION":
                branch_name_is_branch_version = value
    if branch_name_is_branch_version:
        if branch_version is None:
            raise ValueError(
                "BRANCH_NAME_IS_BRANCH_VERSION is set but BRANCH_VERSION is missing in defines.make"
            )
        return branch_version
    return "master"


def all_requirements_files() -> list[Path]:
    """Return all (dev-)requirements.in files across the repo."""
    root = bazel_repo_root()
    # no need to look for requirements.in-* files, since those are aggregated into requirements.in
    return list(root.glob("**/*/requirements.in")) + list(root.glob("**/*/dev-requirements.in"))


def parse_requirements_file(file_path: Path) -> dict[str, str]:
    """Parse a requirements file and return a dict of {package_name: version}."""
    result: dict[str, str] = {}
    with open(file_path) as f:
        for req in requirements.parse(f):
            name = cast(str | None, req.name)
            if name is not None:
                result[name] = req.specs[0][1] if req.specs else ""
    return result
