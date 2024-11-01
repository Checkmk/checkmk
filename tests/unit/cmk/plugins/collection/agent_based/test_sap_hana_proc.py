#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.register import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.lib.sap_hana import ParsedSection


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
                ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
                ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
            ],
            {
                "HXE 90 SYSTEMDB - compileserver": {
                    "acting": "YES",
                    "coordin": "NONE",
                    "detail": "",
                    "pid": "3546",
                    "port": "39010",
                    "sql_port": 0,
                },
                "HXE 90 SYSTEMDB - daemon": {
                    "acting": "YES",
                    "coordin": "NONE",
                    "detail": "",
                    "pid": "2384",
                    "port": "39000",
                    "sql_port": 0,
                },
                "HXE 90 SYSTEMDB - webdispatcher": {
                    "acting": "YES",
                    "coordin": "NONE",
                    "detail": "",
                    "pid": "4644",
                    "port": "39006",
                    "sql_port": 0,
                },
            },
        ),
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000"],
            ],
            {},
        ),
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "a", "NONE"],
            ],
            {
                "HXE 90 SYSTEMDB - daemon": {
                    "acting": "YES",
                    "coordin": "NONE",
                    "detail": "",
                    "pid": "2384",
                    "port": "39000",
                    "sql_port": None,
                },
            },
        ),
    ],
)
def test_parse_sap_hana_proc(
    agent_based_plugins: AgentBasedPlugins,
    info: StringTable,
    expected_result: ParsedSection,
) -> None:
    section_plugin = agent_based_plugins.agent_sections[SectionName("sap_hana_proc")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
                ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
                ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
            ],
            [
                Service(item="HXE 90 SYSTEMDB - daemon", parameters={"coordin": "NONE"}),
                Service(item="HXE 90 SYSTEMDB - webdispatcher", parameters={"coordin": "NONE"}),
                Service(item="HXE 90 SYSTEMDB - compileserver", parameters={"coordin": "NONE"}),
            ],
        ),
    ],
)
def test_inventory_sap_hana_proc(
    agent_based_plugins: AgentBasedPlugins, info: StringTable, expected_result: DiscoveryResult
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("sap_hana_proc")].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_proc")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, params, info, expected_result",
    [
        (
            "HXE 90 SYSTEMDB - daemon",
            {"coordin": "NONE"},
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
                ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
                ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
            ],
            [Result(state=State.OK, summary="Port: 39000, PID: 2384")],
        ),
        (
            "HXE 90 SYSTEMDB - daemon",
            {"coordin": "NOT NONE"},
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
            ],
            [
                Result(state=State.OK, summary="Port: 39000, PID: 2384"),
                Result(state=State.WARN, summary="Role: changed from NOT NONE to NONE"),
            ],
        ),
        (
            "HXE 90 SYSTEMDB - daemon",
            {"coordin": "NONE"},
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "YES", "12", "NONE"],
            ],
            [
                Result(state=State.OK, summary="Port: 39000, PID: 2384"),
                Result(state=State.OK, summary="SQL-Port: 12"),
            ],
        ),
        (
            "HXE 90 SYSTEMDB - daemon",
            {"coordin": "SOMETHING"},
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["39000", "daemon", "2384", "", "NO", "0", "SOMETHING"],
            ],
            [
                Result(state=State.OK, summary="Port: 39000, PID: 2384"),
                Result(state=State.OK, summary="Role: SOMETHING"),
                Result(state=State.CRIT, summary="not acting"),
            ],
        ),
    ],
)
def test_check_sap_hana_proc(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    params: Mapping[str, str],
    info: StringTable,
    expected_result: CheckResult,
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("sap_hana_proc")].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_proc")]
    assert list(plugin.check_function(item, params, section)) == expected_result
