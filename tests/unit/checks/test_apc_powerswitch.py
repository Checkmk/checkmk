#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@pytest.fixture(name="check")
def _apc_powerswitch_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("apc_powerswitch")]


@pytest.fixture(name="string_table")
def _string_table() -> StringTable:
    return [
        ["1", "Rubrik rbot2 1-4", "1"],
        ["2", "C13 NOT IN USE", "1"],
        ["3", "Sampo 2A", "1"],
        ["24", "C19 NOT IN USE", ""],
    ]


def test_discover_apc_powerswitch(check: CheckPlugin, string_table: StringTable) -> None:
    assert list(check.discovery_function(string_table)) == [
        Service(item="1", parameters={"auto-migration-wrapper-key": 1}),
        Service(item="2", parameters={"auto-migration-wrapper-key": 1}),
        Service(item="3", parameters={"auto-migration-wrapper-key": 1}),
    ]


def test_discover_apc_powerswitch_no_items(check: CheckPlugin) -> None:
    assert list(check.discovery_function([])) == []


def test_check_apc_powerswitch_item_not_found(
    check: CheckPlugin, string_table: StringTable
) -> None:
    assert list(check.check_function(item="Not there", params={}, section=string_table)) == [
        Result(state=State.UNKNOWN, summary="Port not found")
    ]


def test_check_apc_powerswitch(check: CheckPlugin, string_table: StringTable) -> None:
    assert list(check.check_function(item="1", params={}, section=string_table)) == [
        Result(state=State.OK, summary="Port Rubrik rbot2 1-4 has status on"),
    ]


def test_check_apc_powerswitch_weird_state(check: CheckPlugin, string_table: StringTable) -> None:
    # This is not a desired behaviour and should be corrected with the migration
    with pytest.raises(KeyError):
        list(check.check_function(item="24", params={}, section=string_table))
