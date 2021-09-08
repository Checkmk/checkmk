#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
)


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["open_events", "4"],
                ["disabled_alerts", "1"],
                ["high_alerts", "0"],
            ],
            {
                "HXE 90 SYSTEMDB": {"disabled_alerts": 1, "high_alerts": 0, "open_events": 4},
            },
        ),
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["open_events", "a"],
                ["disabled_alerts"],
                ["high_alerts", "0"],
            ],
            {
                "HXE 90 SYSTEMDB": {
                    "high_alerts": 0,
                },
            },
        ),
    ],
)
def test_parse_sap_hana_events(fix_register, info, expected_result):
    section_plugin = fix_register.agent_sections[SectionName("sap_hana_events")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["open_events", "4"],
                ["disabled_alerts", "1"],
                ["high_alerts", "0"],
            ],
            [Service(item="HXE 90 SYSTEMDB")],
        ),
    ],
)
def test_inventory_sap_hana_events(fix_register, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_events")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_events")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 90 SYSTEMDB",
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["open_events", "4"],
                ["disabled_alerts", "1"],
                ["high_alerts", "0"],
            ],
            [
                Result(state=State.CRIT, summary="Unacknowledged events: 4"),
                Metric("num_open_events", 4),
                Result(state=State.WARN, summary="Disabled alerts: 1"),
                Metric("num_disabled_alerts", 1),
                Result(state=State.OK, summary="High alerts: 0"),
                Metric("num_high_alerts", 0),
            ],
        ),
        (
            "HXE 90 SYSTEMDB",
            [
                ["[[HXE 90 SYSTEMDB]]"],
                ["unknown_events", "4"],
            ],
            [
                Result(state=State.UNKNOWN, summary="unknown[unknown_events]: 4"),
                Metric("num_unknown_events", 4),
            ],
        ),
    ],
)
def test_check_sap_hana_events(fix_register, item, info, expected_result):
    section = fix_register.agent_sections[SectionName("sap_hana_events")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_events")]
    assert list(plugin.check_function(item, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 90 SYSTEMDB",
            [
                ["[[HXE 90 SYSTEMDB]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_events_stale(fix_register, item, info):
    section = fix_register.agent_sections[SectionName("sap_hana_events")].parse_function(info)
    plugin = fix_register.check_plugins[CheckPluginName("sap_hana_events")]
    with pytest.raises(IgnoreResultsError):
        list(plugin.check_function(item, section))
