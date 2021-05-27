#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
        ["39006", "webdispatcher", "4644", "", "YES", "0", "NONE"],
        ["39010", "compileserver", "3546", "", "YES", "0", "NONE"],
    ], {
        "HXE 90 SYSTEMDB - compileserver": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "3546",
            "port": "39010",
            "sql_port": 0
        },
        "HXE 90 SYSTEMDB - daemon": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "2384",
            "port": "39000",
            "sql_port": 0
        },
        "HXE 90 SYSTEMDB - webdispatcher": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "4644",
            "port": "39006",
            "sql_port": 0
        },
    }),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000"],
    ], {}),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["39000", "daemon", "2384", "", "YES", "a", "NONE"],
    ], {
        "HXE 90 SYSTEMDB - daemon": {
            "acting": "YES",
            "coordin": "NONE",
            "detail": "",
            "pid": "2384",
            "port": "39000",
            "sql_port": None
        },
    }),
])
def test_parse_sap_hana_proc(info, expected_result):
    section_name = SectionName("sap_hana_proc")
    section_plugin = register.get_section_plugin(section_name)
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
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
            Service(item="HXE 90 SYSTEMDB - compileserver", parameters={"coordin": "NONE"})
        ],
    ),
])
def test_inventory_sap_hana_proc(info, expected_result):
    section_name = SectionName("sap_hana_proc")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_proc")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("item, params, info, expected_result", [
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "NONE"
        },
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
        {
            "coordin": "NOT NONE"
        },
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["39000", "daemon", "2384", "", "YES", "0", "NONE"],
        ],
        [
            Result(state=State.OK, summary="Port: 39000, PID: 2384"),
            Result(state=State.WARN, summary="Role: changed from NOT NONE to NONE")
        ],
    ),
    (
        "HXE 90 SYSTEMDB - daemon",
        {
            "coordin": "NONE"
        },
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
        {
            "coordin": "SOMETHING"
        },
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
])
def test_check_sap_hana_proc(item, params, info, expected_result):
    section_name = SectionName("sap_hana_proc")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_proc")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.check_function(item, params, section)) == expected_result
