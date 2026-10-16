#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json

import pytest

from cmk.agent_based.v2 import Service, StringTable
from cmk.plugins.redfish.agent_based.redfish_temperatures import discovery_redfish_temperatures
from cmk.plugins.redfish.lib import parse_redfish_multiple, RedfishAPIData


def _thermal_section(*temperatures: dict[str, object]) -> RedfishAPIData:
    entry = {
        "@odata.id": "/redfish/v1/Chassis/System.Embedded.1/Thermal",
        "@odata.type": "#Thermal.v1_4_0.Thermal",
        "Id": "Thermal",
        "Temperatures": list(temperatures),
    }
    string_table: StringTable = [[json.dumps(entry)]]
    return parse_redfish_multiple(string_table)


@pytest.mark.xfail(
    strict=True, reason="Crash report 46c9cbe6-c8c7-11f1-8e06-bc2411416c01: AttributeError"
)
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

    assert list(discovery_redfish_temperatures(_thermal_section(placeholder, sensor))) == [
        Service(item="CPU1 Temp")
    ]
