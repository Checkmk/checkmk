#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="check")
def _apc_mod_pdu_modules_check_plugin() -> Check:
    return Check("apc_mod_pdu_modules")


@pytest.fixture(name="string_table")
def _string_table() -> StringTable:
    return [
        ["Circuit 1a", "1", "12"],
        ["Circuit 1b", "1", "13"],
        ["Circuit 1c", "1", "8"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["Circuit 3a", "1", "22"],
        ["Circuit 3b", "1", "6"],
        ["Circuit 3c", "1", "0"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
        ["", "-1", "-1"],
    ]


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_apc_mod_pdu_modules(check: Check, string_table: StringTable) -> None:
    assert list(check.run_discovery(string_table)) == [
        ("Circuit 1a", None),
        ("Circuit 1b", None),
        ("Circuit 1c", None),
        ("Circuit 3a", None),
        ("Circuit 3b", None),
        ("Circuit 3c", None),
    ]


@pytest.mark.usefixtures("config_load_all_checks")
def test_discover_apc_mod_pdu_modules_no_items(check: Check) -> None:
    assert list(check.run_discovery([])) == []


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_apc_mod_pdu_modules(check: Check, string_table: StringTable) -> None:
    assert check.run_check("Circuit 1a", {}, string_table) == (0, "Status normal, current: 1.20kw ",
                                                               [("current_power", 1.2)])


@pytest.mark.usefixtures("config_load_all_checks")
def test_check_apc_mod_pdu_modules_vanished_item(check: Check, string_table: StringTable) -> None:
    assert check.run_check("Not there", {}, string_table) == (3, "Module not found")
