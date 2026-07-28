#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

from tests.testlib.common.repo import repo_path


class _PnpmSection(BaseModel, frozen=True):
    overrides: Mapping[str, str] = {}


class _PackageJson(BaseModel, frozen=True):
    pnpm: _PnpmSection = _PnpmSection()
    override_docs: Mapping[str, str] = Field(default={}, alias="// pnpm overrides")


def _load_package_json(package_json_path: Path) -> _PackageJson:
    return _PackageJson.model_validate_json((repo_path() / package_json_path).read_text())


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
    package_json = _load_package_json(Path(package_json_path))

    if not package_json.pnpm.overrides:
        assert not package_json.override_docs, (
            f"{package_json_path}: Found '// pnpm overrides' documentation but no pnpm.overrides section. "
            "Remove the documentation if no overrides exist."
        )
        return

    assert package_json.override_docs, (
        f"{package_json_path}: pnpm.overrides section exists but '// pnpm overrides' documentation is missing. "
        "Add documentation for all overrides."
    )

    for package_name in package_json.pnpm.overrides:
        assert package_name in package_json.override_docs, (
            f"{package_json_path}: Override '{package_name}' is missing from documentation section '// pnpm overrides'"
        )

        ticket = package_json.override_docs[package_name]
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
    package_json = _load_package_json(Path(package_json_path))

    if not package_json.pnpm.overrides:
        assert not package_json.override_docs, (
            f"{package_json_path}: Found '// pnpm overrides' documentation but no pnpm.overrides section exists"
        )
        return

    for package_name in package_json.override_docs:
        assert package_name in package_json.pnpm.overrides, (
            f"{package_json_path}: Package '{package_name}' is documented in '// pnpm overrides' "
            f"but not present in pnpm.overrides"
        )
