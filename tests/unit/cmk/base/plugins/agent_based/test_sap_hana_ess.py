#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.api.agent_based import register
from cmk.utils.type_defs import SectionName, CheckPluginName
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, State, Service, Metric, IgnoreResultsError


@pytest.mark.usefixtures("load_all_agent_based_plugins")
@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no",
                "started": 0
            }
        },
    ),
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no"
            }
        },
    ),
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started", "a"],
            ["active", "no"],
        ],
        {
            "HXE 90 HXE": {
                "active": "no"
            }
        },
    ),
])
def test_parse_sap_hana_ess(info, expected_result):
    section_name = SectionName("sap_hana_ess")
    section_plugin = register.get_section_plugin(section_name)
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.parametrize("info, expected_result", [
    (
        [
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        [Service(item="HXE 90 HXE")],
    ),
])
def test_inventory_sap_hana_ess(info, expected_result):
    section_name = SectionName("sap_hana_ess")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_ess")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize("item, info, expected_result", [
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "0"],
            ["active", "no"],
        ],
        [
            Result(state=State.CRIT, summary="Active status: no"),
            Result(state=State.CRIT, summary="Started threads: 0"),
            Metric("threads", 0)
        ],
    ),
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "1"],
            ["active", "yes"],
        ],
        [
            Result(state=State.OK, summary="Active status: yes"),
            Result(state=State.OK, summary="Started threads: 1"),
            Metric("threads", 1),
        ],
    ),
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
            ["started", "1"],
            ["active", "unknown"],
        ],
        [
            Result(state=State.UNKNOWN, summary="Active status: unknown"),
            Result(state=State.OK, summary="Started threads: 1"),
            Metric("threads", 1),
        ],
    ),
])
def test_check_sap_hana_ess(item, info, expected_result):
    section_name = SectionName("sap_hana_ess")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_ess")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        assert list(plugin.check_function(item, section)) == expected_result


@pytest.mark.parametrize("item, info", [
    (
        "HXE 90 HXE",
        [
            ["[[HXE 90 HXE]]"],
        ],
    ),
])
def test_check_sap_hana_ess_stale(item, info):
    section_name = SectionName("sap_hana_ess")
    section = register.get_section_plugin(section_name).parse_function(info)

    plugin_name = CheckPluginName("sap_hana_ess")
    plugin = register.get_check_plugin(plugin_name)
    if plugin:
        with pytest.raises(IgnoreResultsError):
            list(plugin.check_function(item, section))
