#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service, Metric


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["mem_rate", "5115896693", "7297159168"],
        ],
        {
            "HXE 90 SYSTEMDB": {
                "total": 7297159168,
                "used": 5115896693
            }
        },
    ),
    (
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["5115896693", "7297159168", "mem_rate"],
        ],
        {},
    ),
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["mem_rate", "5115896693a", "7297159168"],
    ], {
        "HXE 90 SYSTEMDB": {
            "total": 7297159168
        }
    }),
])
def test_parse_sap_hana_memrate(info, expected_result):
    section_name = SectionName("sap_hana_memrate")
    section_plugin = register.get_section_plugin(section_name)
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    ([
        ["[[HXE 90 SYSTEMDB]]"],
        ["mem_rate", "5115896693", "7297159168"],
    ], [Service(item="HXE 90 SYSTEMDB")]),
])
def test_inventory_sap_hana_memrate(info, expected_result):
    section_name = SectionName("sap_hana_memrate")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_memrate")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 SYSTEMDB",
        [
            ["[[HXE 90 SYSTEMDB]]"],
            ["mem_rate", "5115896693", "7297159168"],
        ],
        [
            Result(state=State.OK, summary="Usage: 70.11% - 4.76 GiB of 6.80 GiB"),
            Metric("memory_used", 5115896693.0, boundaries=(0.0, 7297159168.0))
        ],
    ),
])
def test_check_sap_hana_memrate(item, info, expected_result):
    section_name = SectionName("sap_hana_memrate")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_memrate")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.check_function(item, {}, section)) == expected_result
