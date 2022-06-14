#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State


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
def test_parse_sap_hana_proc(fix_register, info, expected_result) -> None:
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_proc")]
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
def test_inventory_sap_hana_proc(fix_register, info, expected_result) -> None:
    section = fix_register.agent_sections[SectionName("sap_hana_proc")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_proc")]
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
def test_check_sap_hana_proc(fix_register, item, params, info, expected_result) -> None:
    section = fix_register.agent_sections[SectionName("sap_hana_proc")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_proc")]
    assert list(plugin.check_function(item, params, section)) == expected_result
