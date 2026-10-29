#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_fans import check_redfish_fans, discovery_redfish_fans
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_HEALTHY = {"Health": "OK", "State": "Enabled"}


def _thermal_section(*fans: Mapping[str, object]) -> RedfishAPIData:
    entry = {
        "@odata.id": "/redfish/v1/Chassis/1/Thermal",
        "@odata.type": "#Thermal.v1_4_0.Thermal",
        "Id": "Thermal",
        "Fans": list(fans),
    }
    string_table: StringTable = [[json.dumps(entry)]]
    return parse_redfish_multiple(string_table)


def test_fans_are_discovered_without_a_leading_fan_in_their_name() -> None:
    section = _thermal_section(
        {"Name": "Fan 1", "Status": _HEALTHY},
        {"Name": "System Fan 2", "Status": _HEALTHY},
    )

    assert list(discovery_redfish_fans(section)) == [
        Service(item="1"),
        Service(item="System Fan 2"),
    ]


def test_fans_are_discovered_by_their_legacy_fan_name() -> None:
    section = _thermal_section({"FanName": "Fan 3", "Status": _HEALTHY})

    assert list(discovery_redfish_fans(section)) == [Service(item="3")]


def test_absent_fans_are_not_discovered() -> None:
    section = _thermal_section({"Name": "Fan 1", "Status": {"State": "Absent"}})

    assert list(discovery_redfish_fans(section)) == []


def test_fans_without_a_name_are_not_discovered() -> None:
    section = _thermal_section({"Reading": 3000, "Status": _HEALTHY})

    assert list(discovery_redfish_fans(section)) == []


def test_fan_speed_in_percent_is_reported() -> None:
    section = _thermal_section(
        {"Name": "Fan 1", "Reading": 45, "ReadingUnits": "Percent", "Status": _HEALTHY}
    )

    assert list(check_redfish_fans("1", section)) == [
        Result(state=State.OK, summary="Speed: 45.0%"),
        Metric("perc", 45.0, boundaries=(0.0, 100.0)),
        Result(state=State.OK, notice="Component State: Normal, This resource is enabled."),
    ]


def test_fan_speed_in_rpm_is_reported() -> None:
    section = _thermal_section(
        {"Name": "Fan 1", "Reading": 3000, "ReadingUnits": "RPM", "Status": _HEALTHY}
    )

    assert list(check_redfish_fans("1", section)) == [
        Result(state=State.OK, summary="Speed: 3000.0 rpm"),
        Metric("fan", 3000.0),
        Result(state=State.OK, notice="Component State: Normal, This resource is enabled."),
    ]


def test_fan_speed_without_unit_is_assumed_to_be_rpm() -> None:
    section = _thermal_section({"Name": "Fan 1", "Reading": 3000, "Status": _HEALTHY})

    assert list(check_redfish_fans("1", section)) == [
        Result(state=State.OK, summary="Speed: 3000.0 rpm"),
        Metric("fan", 3000.0),
        Result(state=State.OK, summary="No unit found assume RPM!"),
        Result(state=State.OK, notice="Component State: Normal, This resource is enabled."),
    ]


def test_fan_below_its_lower_critical_threshold_is_crit() -> None:
    section = _thermal_section(
        {
            "Name": "Fan 1",
            "Reading": 500,
            "ReadingUnits": "RPM",
            "LowerThresholdCritical": 1000,
            "Status": _HEALTHY,
        }
    )

    assert list(check_redfish_fans("1", section))[0] == Result(
        state=State.CRIT, summary="Speed: 500.0 rpm (warn/crit below 1000.0 rpm/1000.0 rpm)"
    )


def test_fan_without_reading_reports_no_performance_data() -> None:
    section = _thermal_section({"Name": "Fan 1", "Status": _HEALTHY})

    assert list(check_redfish_fans("1", section))[0] == Result(
        state=State.OK, summary="No performance data found"
    )


def test_critical_fan_health_makes_the_service_crit() -> None:
    section = _thermal_section(
        {
            "Name": "Fan 1",
            "Reading": 3000,
            "ReadingUnits": "RPM",
            "Status": {"Health": "Critical", "State": "Enabled"},
        }
    )

    assert list(check_redfish_fans("1", section))[-1] == Result(
        state=State.CRIT,
        notice="Component State: A critical condition requires immediate attention., "
        "This resource is enabled.",
    )


def test_vanished_fan_yields_no_result() -> None:
    section = _thermal_section({"Name": "Fan 1", "Reading": 3000, "Status": _HEALTHY})

    assert list(check_redfish_fans("2", section)) == []
