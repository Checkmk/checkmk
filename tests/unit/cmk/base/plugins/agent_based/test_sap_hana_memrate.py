#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["mem_rate", "5115896693", "7297159168"],
            ],
            {"HXE 90 SYSTEMDB": {"total": 7297159168, "used": 5115896693}},
        ),
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["5115896693", "7297159168", "mem_rate"],
            ],
            {"HXE 90 SYSTEMDB": {}},
        ),
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["mem_rate", "5115896693a", "7297159168"],
            ],
            {"HXE 90 SYSTEMDB": {"total": 7297159168}},
        ),
    ],
)
def test_parse_sap_hana_memrate(fix_register, info, expected_result):
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_memrate")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["mem_rate", "5115896693", "7297159168"],
            ],
            [Service(item="HXE 90 SYSTEMDB")],
        ),
    ],
)
def test_inventory_sap_hana_memrate(fix_register, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_memrate")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_memrate")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 90 SYSTEMDB",
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["mem_rate", "5115896693", "7297159168"],
            ],
            [
                Result(state=State.OK, summary="Usage: 70.11% - 4.76 GiB of 6.80 GiB"),
                Metric("memory_used", 5115896693.0, boundaries=(0.0, 7297159168.0)),
            ],
        ),
    ],
)
def test_check_sap_hana_memrate(fix_register, item, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_memrate")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_memrate")]
    assert list(plugin.check_function(item, {}, section)) == expected_result
