#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="check")
def _apc_mod_pdu_modules_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("apc_mod_pdu_modules")]


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


def test_discover_apc_mod_pdu_modules(check: CheckPlugin, string_table: StringTable) -> None:
    assert list(check.discovery_function(string_table)) == [
        Service(item="Circuit 1a"),
        Service(item="Circuit 1b"),
        Service(item="Circuit 1c"),
        Service(item="Circuit 3a"),
        Service(item="Circuit 3b"),
        Service(item="Circuit 3c"),
    ]


def test_discover_apc_mod_pdu_modules_no_items(check: CheckPlugin) -> None:
    assert list(check.discovery_function([])) == []


def test_check_apc_mod_pdu_modules(check: CheckPlugin, string_table: StringTable) -> None:
    assert list(check.check_function(item="Circuit 1a", params={}, section=string_table)) == [
        Result(state=State.OK, summary="Status normal, current: 1.20kw"),
        Metric("current_power", 1.2),
    ]


def test_check_apc_mod_pdu_modules_vanished_item(
    check: CheckPlugin, string_table: StringTable
) -> None:
    assert list(check.check_function(item="Not there", params={}, section=string_table)) == [
        Result(state=State.UNKNOWN, summary="Module not found")
    ]
