#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Result,
    Service,
    State,
)


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            {"HXE 98": "OK"},
        )
    ],
)
def test_parse_sap_hana_db_status(fix_register, info, expected_result):
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_db_status")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            [Service(item="HXE 98")],
        ),
    ],
)
def test_inventory_sap_hana_db_status(fix_register, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["OK"],
            ],
            [Result(state=State.OK, summary="OK")],
        ),
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["DB status failed: * -10104: Invalid value for KEY"],
            ],
            [Result(state=State.CRIT, summary="DB status failed: * -10104: Invalid value for KEY")],
        ),
    ],
)
def test_check_sap_hana_db_status(fix_register, item, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    assert list(plugin.check_function(item, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_db_status_stale(fix_register, item, info):
    section = fix_register.agent_sections[SectionName("sap_hana_db_status")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_db_status")]
    with pytest.raises(IgnoreResultsError):
        list(plugin.check_function(item, section))
