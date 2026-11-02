#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_voltage import (
    check_redfish_voltage,
    discovery_redfish_voltage,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData

_HEALTHY = {"Health": "OK", "State": "Enabled"}


def _power_entry(chassis: str, *voltages: Mapping[str, object]) -> dict[str, object]:
    entry: dict[str, object] = {
        "@odata.id": f"/redfish/v1/Chassis/{chassis}/Power",
        "@odata.type": "#Power.v1_5_0.Power",
        "Id": "Power",
    }
    if voltages:
        entry["Voltages"] = list(voltages)
    return entry


def _power_section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [[json.dumps(entry)] for entry in entries]
    return parse_redfish_multiple(string_table)


def test_voltages_with_a_reading_are_discovered_by_name() -> None:
    section = _power_section(
        _power_entry("1", {"Name": "CPU1 VCORE", "ReadingVolts": 1.8, "Status": _HEALTHY})
    )

    assert list(discovery_redfish_voltage(section)) == [Service(item="CPU1 VCORE")]


def test_voltages_without_a_reading_are_not_discovered() -> None:
    section = _power_section(
        _power_entry("1", {"Name": "CPU1 VCORE", "ReadingVolts": None, "Status": _HEALTHY})
    )

    assert list(discovery_redfish_voltage(section)) == []


def test_voltages_without_a_name_are_not_discovered() -> None:
    section = _power_section(
        _power_entry("1", {"Name": None, "ReadingVolts": 1.8, "Status": _HEALTHY})
    )

    assert list(discovery_redfish_voltage(section)) == []


def test_discovery_continues_past_a_chassis_without_voltages() -> None:
    section = _power_section(
        _power_entry("1"),
        _power_entry("2", {"Name": "PS1 Voltage", "ReadingVolts": 230, "Status": _HEALTHY}),
    )

    assert list(discovery_redfish_voltage(section)) == [Service(item="PS1 Voltage")]


def test_voltage_location_and_sensor_number_are_reported() -> None:
    section = _power_section(
        _power_entry(
            "1",
            {
                "Name": "CPU1 VCORE",
                "ReadingVolts": 1.8,
                "PhysicalContext": "CPU",
                "SensorNumber": 17,
                "Status": _HEALTHY,
            },
        )
    )

    assert list(check_redfish_voltage("CPU1 VCORE", section))[0] == Result(
        state=State.OK, summary="Location: CPU, SensorNr: 17"
    )


def test_voltage_reading_is_reported_with_its_metric() -> None:
    section = _power_section(
        _power_entry("1", {"Name": "CPU1 VCORE", "ReadingVolts": 1.8, "Status": _HEALTHY})
    )

    assert list(check_redfish_voltage("CPU1 VCORE", section))[1:3] == [
        Result(state=State.OK, summary="Value: 1.8 V"),
        Metric("voltage", 1.8),
    ]


def test_check_continues_past_a_chassis_without_voltages() -> None:
    section = _power_section(
        _power_entry("1"),
        _power_entry("2", {"Name": "PS1 Voltage", "ReadingVolts": 230, "Status": _HEALTHY}),
    )

    assert list(check_redfish_voltage("PS1 Voltage", section))[1] == Result(
        state=State.OK, summary="Value: 230.0 V"
    )


def test_voltage_above_its_upper_critical_threshold_is_crit() -> None:
    section = _power_section(
        _power_entry(
            "1",
            {
                "Name": "PS1 Voltage",
                "ReadingVolts": 260,
                "UpperThresholdCritical": 250,
                "Status": _HEALTHY,
            },
        )
    )

    assert list(check_redfish_voltage("PS1 Voltage", section))[1] == Result(
        state=State.CRIT, summary="Value: 260.0 V (warn/crit at 250.0 V/250.0 V)"
    )


def test_voltage_without_reading_reports_no_voltage_data() -> None:
    section = _power_section(
        _power_entry("1", {"Name": "CPU1 VCORE", "ReadingVolts": None, "Status": _HEALTHY})
    )

    assert list(check_redfish_voltage("CPU1 VCORE", section))[1] == Result(
        state=State.OK, summary="No voltage data found"
    )


def test_critical_voltage_health_makes_the_service_crit() -> None:
    section = _power_section(
        _power_entry(
            "1",
            {
                "Name": "CPU1 VCORE",
                "ReadingVolts": 1.8,
                "Status": {"Health": "Critical", "State": "Enabled"},
            },
        )
    )

    assert list(check_redfish_voltage("CPU1 VCORE", section))[-1] == Result(
        state=State.CRIT,
        notice="Component State: A critical condition requires immediate attention., "
        "This resource is enabled.",
    )


def test_vanished_voltage_yields_no_result() -> None:
    section = _power_section(
        _power_entry("1", {"Name": "CPU1 VCORE", "ReadingVolts": 1.8, "Status": _HEALTHY})
    )

    assert list(check_redfish_voltage("CPU2 VCORE", section)) == []
