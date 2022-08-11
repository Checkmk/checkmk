#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest

import cmk.utils.msi_engine as msi_engine

EXPECTED_P_WITH_HASH: Final = msi_engine._Parameters(
    msi=Path("msi"),
    src_dir=Path("dir"),
    revision="rev",
    version="vers",
    package_code_hash="hash",
)

EXPECTED_P_NO_HASH: Final = msi_engine._Parameters(
    msi=Path("msi"),
    src_dir=Path("dir"),
    revision="rev",
    version="vers",
    package_code_hash=None,
)


@pytest.mark.parametrize(
    "cmd_line, parameters, opt_verbose",
    [
        (["stub", "msi", "dir", "rev", "vers"], EXPECTED_P_NO_HASH, False),
        (["stub", "-v", "msi", "dir", "rev", "vers", "hash"], EXPECTED_P_WITH_HASH, True),
        (["stub", "-v", "msi", "dir", "rev", "vers"], EXPECTED_P_NO_HASH, True),
    ],
)
def test_parse_command_line(
    cmd_line: Sequence[str], parameters: msi_engine._Parameters, opt_verbose: bool
) -> None:
    assert msi_engine.parse_command_line(cmd_line) == parameters
    assert msi_engine.opt_verbose == opt_verbose


EXPECTED_FILE_TABLE: Final = sorted(
    ["check_mk_install_yml", "checkmk.dat", "plugins_cap", "python_3.cab"]
)

EXPECTED_COMPONENT_TABLE: Final = sorted(
    [
        "check_mk_install_yml_",
        "checkmk.dat",
        "plugins_cap_",
        "python_3.cab",
    ]
)


# check of constants: we do noy want to break build after soem refactoring, renaming or typo-fix
def test_msi_tables() -> None:
    assert msi_engine.msi_file_table() == EXPECTED_FILE_TABLE
    assert msi_engine.msi_component_table() == EXPECTED_COMPONENT_TABLE


@pytest.mark.parametrize(
    "version, expected",
    [
        ("1.7.0i1", "1.7.0.xxx"),
        ("1.2.5i4p1", "1.2.5.xxx"),
        ("2015.04.12", "15.4.12.xxx"),
        ("2.0.0i1", "2.0.0.xxx"),
        ("1.6.0-2020.02.20", "1.6.0.xxx"),
    ],
)
def test_generate_product_versions(version: str, expected: str) -> None:
    assert msi_engine.generate_product_version(version, revision_text="xxx") == expected
