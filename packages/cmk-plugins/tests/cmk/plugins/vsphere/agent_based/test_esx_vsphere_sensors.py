#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Final, Never

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.vsphere.agent_based.esx_vsphere_sensors import (
    check_esx_vsphere_sensors,
    inventory_esx_vsphere_sensors,
    parse_esx_vsphere_sensors,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "VMware Rollup Health State",
                    "",
                    "0",
                    "system",
                    "0",
                    "",
                    "red",
                    "Red",
                    "Sensor is operating under critical conditions",
                ],
                [
                    "Power Domain 1 Power Unit 0 - Redundancy lost",
                    "",
                    "0",
                    "power",
                    "0",
                    "",
                    "yellow",
                    "Yellow",
                    "Sensor is operating under conditions that are non-critical",
                ],
                [
                    "Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert",
                    "",
                    "0",
                    "power",
                    "0",
                    "",
                    "red",
                    "Red",
                    "Sensor is operating under critical conditions",
                ],
                ["Dummy sensor", "", "", "", "", "", "green", "all is good", "the sun is shining"],
            ],
            [Service()],
        ),
    ],
)
def test_inventory_esx_vsphere_sensors(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for esx_vsphere_sensors check."""
    parsed = parse_esx_vsphere_sensors(string_table)
    result = list(inventory_esx_vsphere_sensors(parsed))
    assert sorted(result) == sorted(expected_discoveries)


_PARAMS: Mapping[str, Sequence[Never]] = {"rules": []}

_STRING_TABLE: Final = [
    [
        "VMware Rollup Health State",
        "",
        "0",
        "system",
        "0",
        "",
        "red",
        "Red",
        "Sensor is operating under critical conditions",
    ],
    [
        "Power Domain 1 Power Unit 0 - Redundancy lost",
        "",
        "0",
        "power",
        "0",
        "",
        "yellow",
        "Yellow",
        "Sensor is operating under conditions that are non-critical",
    ],
    [
        "Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert",
        "",
        "0",
        "power",
        "0",
        "",
        "red",
        "Red",
        "Sensor is operating under critical conditions",
    ],
    ["Dummy sensor", "", "", "", "", "", "green", "all is good", "the sun is shining"],
]

_EXPECTED_RESULTS: Final = [
    Result(
        state=State.CRIT,
        summary="VMware Rollup Health State: Red (Sensor is operating under critical conditions)",
    ),
    Result(
        state=State.WARN,
        summary="Power Domain 1 Power Unit 0 - Redundancy lost: Yellow (Sensor is operating under conditions that are non-critical)",
    ),
    Result(
        state=State.CRIT,
        summary="Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert: Red (Sensor is operating under critical conditions)",
    ),
    Result(
        state=State.OK,
        notice=(
            "At least one sensor reported. Sensors readings are:\n"
            "VMware Rollup Health State: Red (Sensor is operating under critical conditions)\n"
            "Power Domain 1 Power Unit 0 - Redundancy lost: Yellow (Sensor is operating under conditions that are non-critical)\n"
            "Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert: Red (Sensor is operating under critical conditions)\n"
            "Dummy sensor: all is good (the sun is shining)"
        ),
    ),
]


def test_check_esx_vsphere_sensors() -> None:
    """Test check function for esx_vsphere_sensors check."""
    parsed = parse_esx_vsphere_sensors(_STRING_TABLE)
    result = list(check_esx_vsphere_sensors(_PARAMS, parsed))
    assert result == _EXPECTED_RESULTS
