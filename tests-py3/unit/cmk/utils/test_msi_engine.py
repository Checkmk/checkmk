#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest  # type: ignore[import] # pylint: disable=unused-import

import cmk.utils.msi_engine as msi_engine


def test_parse_command_line():
    msi_file, source_dir, revision, version_name, aghash = msi_engine.parse_command_line(
        ["stub", "msi", "dir", "rev", "vers", "aghash"])
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert aghash == "aghash"
    assert not msi_engine.opt_verbose
    msi_file, source_dir, revision, version_name, aghash = msi_engine.parse_command_line(
        ["stub", "-v", "msi", "dir", "rev", "vers", "aghash"])
    assert msi_file == "msi"
    assert source_dir == "dir"
    assert revision == "rev"
    assert version_name == "vers"
    assert aghash == "aghash"
    assert msi_engine.opt_verbose


# check of constants: we do noy want to break build after soem refactoring, renaming or typo-fix
def test_msi_tables():
    assert msi_engine.msi_file_table() == [
        "check_mk_ini", "check_mk_install_yml", "checkmk.dat", "plugins_cap", "python_3.8.zip"
    ]
    assert msi_engine.msi_component_table() == [
        "check_mk_ini_", "check_mk_install_yml_", "checkmk.dat", "plugins_cap_", "python_3.8.zip"
    ]
