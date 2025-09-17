#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.esx_vsphere_sensors import (
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
            [(None, {})],
        ),
    ],
)
def test_inventory_esx_vsphere_sensors(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for esx_vsphere_sensors check."""
    parsed = parse_esx_vsphere_sensors(string_table)
    result = list(inventory_esx_vsphere_sensors(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"rules": []},
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
            [
                (
                    2,
                    "VMware Rollup Health State: Red (Sensor is operating under critical conditions)",
                ),
                (
                    1,
                    "Power Domain 1 Power Unit 0 - Redundancy lost: Yellow (Sensor is operating under conditions that are non-critical)",
                ),
                (
                    2,
                    "Power Supply 2 Power Supply 2 0: Power Supply AC lost - Assert: Red (Sensor is operating under critical conditions)",
                ),
                (
                    0,
                    "\nAt least one sensor reported. Sensors readings are:\nVMware Rollup Health State: Red (Sensor is operating under critical conditions)\nPower Domain 1 Power Unit 0 - Redundancy lost: Yellow (Sensor is operating under conditions that are non-critical)\nPower Supply 2 Power Supply 2 0: Power Supply AC lost - Assert: Red (Sensor is operating under critical conditions)\nDummy sensor: all is good (the sun is shining)",
                ),
            ],
        ),
    ],
)
def test_check_esx_vsphere_sensors(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for esx_vsphere_sensors check."""
    parsed = parse_esx_vsphere_sensors(string_table)
    result = list(check_esx_vsphere_sensors(item, params, parsed))
    assert result == expected_results
