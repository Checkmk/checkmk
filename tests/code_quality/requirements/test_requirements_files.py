#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import re

import pytest
import requirements

from tests.code_quality.bazel_utils import bazel_repo_root
from tests.code_quality.requirements.utils import (
    all_constraints_files,
    all_requirements_files,
    get_branch,
    parse_requirements_file,
)


@pytest.fixture(name="loaded_requirements")
def loaded_requirements_fixture() -> dict[str, str]:
    all_requirements: dict[str, str] = {}
    for req_file in all_requirements_files():
        all_requirements.update(parse_requirements_file(req_file))
    return all_requirements


@pytest.mark.skipif(
    get_branch() == "master",
    reason="pinning is only enforced in release branches",
)
def test_all_packages_pinned(loaded_requirements: dict[str, str]) -> None:
    # Test implements process as described in:
    # https://wiki.lan.checkmk.net/spaces/DEV/pages/106333650/Creating+a+new+version+branch
    unpinned_packages = [req for req in loaded_requirements if not loaded_requirements[req]]
    assert not unpinned_packages, (
        "The following packages are not pinned: %s. "
        "For the sake of reproducibility, all packages must be pinned to a version!"
    ) % " ,".join(unpinned_packages)


def test_runtime_requirements_are_a_strict_subset_of_all_requirements() -> None:
    reqs = frozenset(parse_requirements_file(bazel_repo_root() / "requirements.txt").items())
    runtime = frozenset(
        parse_requirements_file(bazel_repo_root() / "runtime-requirements.txt").items()
    )
    assert runtime.issubset(reqs), (
        f"The following dependencies are incorrectly pinned: {dict(runtime - reqs)}"
    )


def test_constraints() -> None:
    """Make sure all constraints have a ticket to be removed"""
    constraints_files = all_constraints_files()
    # all_constraints_files() globs the runfiles tree, so a dropped data dependency
    # would leave this test passing vacuously.  Anchor it on the shared file.
    assert bazel_repo_root() / "constraints.txt" in constraints_files, (
        f"constraints.txt not among the discovered constraints files: {constraints_files}"
    )
    offenses = []
    for path in constraints_files:
        with path.open() as constraint_file:
            for r in requirements.parse(constraint_file):
                if re.search(r"\bCMK-\d+\b", r.line):
                    continue
                offenses.append(
                    f"Constraint for {r.name} in {path.name} has no ticket to be removed"
                )
    assert not offenses, "\n".join(offenses)


def test_no_development_packages_in_runtime_requirements() -> None:
    """Test that development/testing libraries are not included in runtime requirements"""
    runtime_requirements = parse_requirements_file(bazel_repo_root() / "runtime-requirements.txt")
    forbidden_prefixes = ["pytest-", "types-"]
    offending_packages = []
    for package_name in runtime_requirements:
        for prefix in forbidden_prefixes:
            if package_name.startswith(prefix):
                offending_packages.append(package_name)
    assert not offending_packages, (
        f"The following development/testing libraries should not be "
        f"in runtime requirements: {offending_packages}"
    )
