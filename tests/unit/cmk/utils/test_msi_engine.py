#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.msi_engine as msi_engine


def test_parse_command_line() -> None:
    msi_file, source_dir, revision, version_name, aghash = msi_engine.parse_command_line(
        ["stub", "msi", "dir", "rev", "vers", "aghash"]
    )
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert aghash == "aghash"
    assert not msi_engine.opt_verbose
    msi_file, source_dir, revision, version_name, aghash = msi_engine.parse_command_line(
        ["stub", "-v", "msi", "dir", "rev", "vers", "aghash"]
    )
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert aghash == "aghash"
    assert msi_engine.opt_verbose


EXPECTED_FILE_TABLE = ["check_mk_install_yml", "checkmk.dat", "plugins_cap", "python_3.cab"]

EXPECTED_COMPONENT_TABLE = [
    "check_mk_install_yml_",
    "checkmk.dat",
    "plugins_cap_",
    "python_3.cab",
]


# check of constants: we do noy want to break build after soem refactoring, renaming or typo-fix
def test_msi_tables() -> None:
    assert msi_engine.msi_file_table() == EXPECTED_FILE_TABLE
    assert msi_engine.msi_component_table() == EXPECTED_COMPONENT_TABLE


def test_msi_file_table() -> None:
    a = msi_engine.msi_file_table()
    assert len(a) == len(EXPECTED_FILE_TABLE)  # size for now(yml, dat & cap, zip)
    a_sorted = sorted(a)
    assert a == a_sorted  # array should be sorted


def test_msi_component_table() -> None:
    a = msi_engine.msi_component_table()
    assert len(a) == len(EXPECTED_COMPONENT_TABLE)  # size now(yml, dat & cap, zip)
    a_sorted = sorted(a)
    assert a == a_sorted  # array should be sorted
