#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.redfish.agent_based.redfish_temperatures import (
    check_redfish_temperatures,
    discovery_redfish_temperatures,
)
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData


def _thermal_entry(chassis: str, *temperatures: Mapping[str, object]) -> dict[str, object]:
    entry: dict[str, object] = {
        "@odata.id": f"/redfish/v1/Chassis/{chassis}/Thermal",
        "@odata.type": "#Thermal.v1_4_0.Thermal",
        "Id": "Thermal",
    }
    if temperatures:
        entry["Temperatures"] = list(temperatures)
    return entry


def _thermal_section(*entries: Mapping[str, object]) -> RedfishAPIData:
    string_table: StringTable = [[json.dumps(entry)] for entry in entries]
    return parse_redfish_multiple(string_table)


def test_discovery_redfish_temperatures_skips_entries_without_data() -> None:
    # Some iDRACs list entries whose fields are all null and that carry no "Status".
    placeholder = dict.fromkeys(
        ("@odata.id", "MemberId", "Name", "ReadingCelsius", "RelatedItem", "SensorNumber")
    )
    sensor = {
        "Name": "CPU1 Temp",
        "ReadingCelsius": 30,
        "Status": {"Health": "OK", "State": "Enabled"},
    }
    section = _thermal_section(_thermal_entry("System.Embedded.1", placeholder, sensor))

    assert list(discovery_redfish_temperatures(section)) == [Service(item="CPU1 Temp")]


def test_check_continues_past_a_chassis_without_temperatures() -> None:
    sensor = {
        "Name": "CPU1 Temp",
        "ReadingCelsius": None,
        "Status": {"Health": "Critical", "State": "Enabled"},
    }
    section = _thermal_section(_thermal_entry("1"), _thermal_entry("2", sensor))

    assert list(check_redfish_temperatures("CPU1 Temp", {}, section)) == [
        Result(state=State.OK, summary="No temperature data found"),
        Result(
            state=State.CRIT,
            notice="Component State: A critical condition requires immediate attention., "
            "This resource is enabled.",
        ),
    ]
