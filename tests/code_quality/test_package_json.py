#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from tests.testlib.common.repo import repo_path


def _test_pnpm_overrides_load_data(package_json_path: Path) -> Mapping[str, Any]:
    with open(repo_path() / package_json_path) as package_json_file:
        result: Mapping[str, Any] = json.load(package_json_file)

    return result


@pytest.mark.parametrize(
    "package_json_path",
    [
        "package.json",
        "packages/cmk-frontend-vue/package.json",
        "packages/cmk-frontend/package.json",
        "packages/cmk-shared-typing/package.json",
        "packages/cmk-werks/package.json",
        "bazel/tools/package.json",
    ],
)
def test_pnpm_overrides_have_documentation(package_json_path: str) -> None:
    data = _test_pnpm_overrides_load_data(Path(package_json_path))

    overrides = data.get("pnpm", {}).get("overrides", {})
    override_docs = data.get("// pnpm overrides", {})

    if not overrides:
        assert not override_docs, (
            f"{package_json_path}: Found '// pnpm overrides' documentation but no pnpm.overrides section. "
            "Remove the documentation if no overrides exist."
        )
        return

    assert override_docs, (
        f"{package_json_path}: pnpm.overrides section exists but '// pnpm overrides' documentation is missing. "
        "Add documentation for all overrides."
    )

    for package_name in overrides.keys():
        assert package_name in override_docs, (
            f"{package_json_path}: Override '{package_name}' is missing from documentation section '// pnpm overrides'"
        )

        ticket = override_docs[package_name]
        assert isinstance(ticket, str), (
            f"{package_json_path}: Documentation for '{package_name}' must be a string ticket number"
        )

        # Validate ticket format (CMK-XXXXX)
        assert ticket.startswith("CMK-"), (
            f"{package_json_path}: Override '{package_name}' has invalid ticket format: '{ticket}' "
            f"(expected format: CMK-XXXXX)"
        )


@pytest.mark.parametrize(
    "package_json_path",
    [
        "package.json",
        "packages/cmk-frontend-vue/package.json",
        "packages/cmk-frontend/package.json",
        "packages/cmk-shared-typing/package.json",
        "packages/cmk-werks/package.json",
        "bazel/tools/package.json",
    ],
)
def test_no_undocumented_overrides_in_documentation(package_json_path: str) -> None:
    data = _test_pnpm_overrides_load_data(Path(package_json_path))

    overrides = data.get("pnpm", {}).get("overrides", {})
    override_docs = data.get("// pnpm overrides", {})

    if not overrides:
        assert not override_docs, (
            f"{package_json_path}: Found '// pnpm overrides' documentation but no pnpm.overrides section exists"
        )
        return

    for package_name in override_docs.keys():
        assert package_name in overrides, (
            f"{package_json_path}: Package '{package_name}' is documented in '// pnpm overrides' "
            f"but not present in pnpm.overrides"
        )
