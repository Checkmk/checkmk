#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.collection.agent_based.sap_hana_events import (
    agent_section_sap_hana_events,
    check_plugin_sap_hana_events,
)
from cmk.plugins.lib.sap_hana import ParsedSection


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
def test_parse_sap_hana_events(
    info: StringTable,
    expected_result: ParsedSection,
) -> None:
    assert agent_section_sap_hana_events.parse_function(info) == expected_result


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
def test_inventory_sap_hana_events(info: StringTable, expected_result: DiscoveryResult) -> None:
    assert (
        list(
            check_plugin_sap_hana_events.discovery_function(
                agent_section_sap_hana_events.parse_function(info)
            )
        )
        == expected_result
    )


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
def test_check_sap_hana_events(
    item: str,
    info: StringTable,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_plugin_sap_hana_events.check_function(
                item, agent_section_sap_hana_events.parse_function(info)
            )
        )
        == expected_result
    )


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
def test_check_sap_hana_events_stale(item: str, info: StringTable) -> None:
    with pytest.raises(IgnoreResultsError):
        list(
            check_plugin_sap_hana_events.check_function(
                item, agent_section_sap_hana_events.parse_function(info)
            )
        )
