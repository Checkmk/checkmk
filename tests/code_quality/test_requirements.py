#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="unreachable"


import re
import subprocess
from pathlib import Path

import pytest

from tests.testlib.common.repo import (
    is_pro_repo,
    repo_path,
)

# Packages intentionally excluded from the python_requirements filegroups
# because they are development-only tools, not part of the product build.
_PYTHON_REQUIREMENTS_EXCLUDED: dict[str, set[str]] = {
    "packages": {"cmk-astrein"},
    "non-free/packages": set(),
}
_DEV_PYTHON_REQUIREMENTS_EXCLUDED: dict[str, set[str]] = {
    "packages": set(),
    "non-free/packages": set(),
}


@pytest.mark.parametrize(
    "packages_rel_path", ["packages", "non-free/packages"] if is_pro_repo() else ["packages"]
)
def test_python_requirements_filegroup_complete(packages_rel_path: str) -> None:
    """Every cmk-* package with requirements.in must be listed in python_requirements."""
    packages_dir = repo_path() / packages_rel_path

    listed = _parse_filegroup_packages(packages_rel_path, "python_requirements")
    on_disk = _packages_with_requirements(packages_dir, "requirements.in")
    excluded = _PYTHON_REQUIREMENTS_EXCLUDED[packages_rel_path]

    missing = on_disk - listed - excluded
    assert not missing, (
        f"Packages with requirements.in not listed in {packages_rel_path}/BUILD "
        f"python_requirements: {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "packages_rel_path", ["packages", "non-free/packages"] if is_pro_repo() else ["packages"]
)
def test_dev_python_requirements_filegroup_complete(packages_rel_path: str) -> None:
    """Every cmk-* package with dev-requirements.in must be listed in dev_python_requirements."""
    packages_dir = repo_path() / packages_rel_path

    listed = _parse_filegroup_packages(packages_rel_path, "dev_python_requirements")
    on_disk = _packages_with_requirements(packages_dir, "dev-requirements.in")
    excluded = _DEV_PYTHON_REQUIREMENTS_EXCLUDED[packages_rel_path]

    missing = on_disk - listed - excluded
    assert not missing, (
        f"Packages with dev-requirements.in not listed in {packages_rel_path}/BUILD "
        f"dev_python_requirements: {sorted(missing)}"
    )


def _parse_filegroup_packages(packages_rel_path: str, group_name: str) -> set[str]:
    """Extract cmk-* package names referenced in a BUILD filegroup via bazel query."""
    target = f"//{packages_rel_path}:{group_name}"
    result = subprocess.run(
        ["bazel", "query", f"deps({target}, 1) - {target}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(re.findall(r"/(cmk-[^:]+):", result.stdout))


def _packages_with_requirements(packages_dir: Path, filename: str) -> set[str]:
    """Find cmk-* packages that provide the given requirements file.

    Uses filesystem scanning instead of bazel query because a package that forgot
    to add exports_files for its requirements.in would be invisible to Bazel.
    Which is exactly the oversight this test is meant to catch.
    """
    result = set()
    for d in packages_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("cmk-"):
            continue

        # Most packages have requirements.in as a plain file on disk
        if (d / filename).is_file():
            result.add(d.name)
            continue

        # Some packages (e.g. cmk-plugins) generate requirements.in as a Bazel
        # target (via concat_files) instead of shipping a plain file.
        if (
            build_file := d / "BUILD"
        ).is_file() and f'name = "{filename}"' in build_file.read_text():
            result.add(d.name)

    return result
