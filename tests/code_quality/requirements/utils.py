#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import ast
import json
import os
import re
import warnings
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import isort
import requirements

from tests.code_quality.bazel_utils import bazel_repo_root

STDLIB_IMPORTS = isort.stdlibs.all.stdlib | {"__future__"}
OWN_PACKAGES = {"cmk", "omdlib", "livestatus", "cmc_proto"}


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


def package_names_to_import_names() -> dict[str, list[str]]:
    """Load the pip package name → import name mapping from the JSON file produced by Bazel."""
    mapping_path = os.environ.get("PIP_PACKAGE_MAPPING")
    if not mapping_path:
        raise RuntimeError("PIP_PACKAGE_MAPPING is not set. This test must be run via Bazel.")
    with Path(mapping_path).open() as f:
        mapping: dict[str, list[str]] = json.load(f)
    return mapping


def collect_third_party_imports(source_files: list[str]) -> set[str]:
    """Return top-level third-party import names found in source files."""
    imports: set[str] = set()
    for rel_path in source_files:
        py_file = bazel_repo_root() / rel_path
        with py_file.open("rb") as f, warnings.catch_warnings():
            tree = ast.parse(f.read(), str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imports.add(node.module.split(".")[0])
    return {normalize(imp) for imp in imports - STDLIB_IMPORTS - OWN_PACKAGES}


def normalize(name: str) -> str:
    return re.sub(r"[-_]+", "-", name.lstrip("_")).lower()


def declared_pkg_imports(requirements_file_path: Path) -> Mapping[str, set[str]]:
    """Return a mapping from declared package names to their possible import names."""
    mapping = package_names_to_import_names()
    declared_packages = parse_requirements_file(requirements_file_path)
    return {
        pkg_name: {normalize(imp) for imp in mapping.get(normalize(pkg_name), [pkg_name])}
        for pkg_name in declared_packages
    }
