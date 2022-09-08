#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base import item_state
from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import SNMPSectionPlugin
from cmk.base.api.agent_based.utils import GetRateError
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


@pytest.fixture(name="check_plugin")
def check_plugin_from_fix_register(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("ucd_diskio")]


@pytest.fixture(name="section_plugin")
def section_plugin_from_fix_register(fix_register: FixRegister) -> SNMPSectionPlugin:
    return fix_register.snmp_sections[SectionName("ucd_diskio")]


@pytest.fixture(name="string_table")
def snmp_section():
    return [
        [
            ["1", "ram0", "0", "0", "0", "0"],
            ["2", "ram1", "0", "0", "0", "0"],
        ]
    ]


def test_discover_ucd_diskio(  # type:ignore[no-untyped-def]
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    discovery_results = list(
        check_plugin.discovery_function(section_plugin.parse_function(string_table))
    )
    assert discovery_results == [
        Service(item="ram0"),
        Service(item="ram1"),
    ]


def test_discover_ucd_diskio_with_empty_section(check_plugin: CheckPlugin) -> None:
    assert list(check_plugin.discovery_function({})) == []


def test_check_ucd_diskio_item_not_found(  # type:ignore[no-untyped-def]
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    assert (
        list(
            check_plugin.check_function(
                item="not_found",
                params={},
                section=section_plugin.parse_function(string_table),
            )
        )
        == []
    )


def test_check_ucd_diskio_raise_get_rate_error(  # type:ignore[no-untyped-def]
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    with pytest.raises(GetRateError):
        list(
            check_plugin.check_function(
                item="ram0",
                params={},
                section=section_plugin.parse_function(string_table),
            )
        )


def test_check_function_first_result_is_ok(  # type:ignore[no-untyped-def]
    check_plugin: CheckPlugin,
    section_plugin: SNMPSectionPlugin,
    string_table,
) -> None:
    for field in ["read_ios", "write_ios", "read_throughput", "write_throughput"]:
        # Setting the previous states, so that the get_rate function doesn't return a GetRateError
        item_state.set_item_state(f"ucd_disk_io_{field}.ram0", (0, 0))

    check_result = list(
        check_plugin.check_function(
            item="ram0",
            params={},
            section=section_plugin.parse_function(string_table),
        )
    )

    assert check_result[0] == Result(state=State.OK, summary="[1]")
    assert len(check_result) == 9  # The first result plus a Result and Metric for every field
