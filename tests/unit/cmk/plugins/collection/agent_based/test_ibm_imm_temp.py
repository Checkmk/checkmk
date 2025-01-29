#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.ibm_imm_temp import (
    _check_ibm_imm_temp,
    discover_ibm_imm_temp,
    parse_ibm_imm_temp,
    SensorTemperature,
)


@pytest.fixture(name="section", scope="module")
def fixture_section() -> dict[str, SensorTemperature]:
    return parse_ibm_imm_temp(
        [
            ["PCH Temp", "45", "98", "93", "0", "0"],
            ["Ambient Temp", "17", "47", "43", "", "0"],
            ["PCI Riser 1 Temp", "25", "80", "70", "0", "0"],
            ["PCI Riser 2 Temp", "0", "0", "0", "0", "0"],
            ["Mezz Card Temp", "0", "0", "0", "0", "0"],
            ["CPU1 VR Temp", "129", "100", "95", "0", "0"],
            ["CPU2 VR Temp", "27", "100", "95", "0", "0"],
            ["DIMM AB VR Temp", "24", "100", "95", "0", "0"],
            ["DIMM CD VR Temp", "25", "100", "95", "0", "0"],
            ["DIMM EF VR Temp", "23", "100", "95", "0", "0"],
            ["DIMM GH VR Temp", "26", "100", "95", "0", "0"],
        ]
    )


def test_inventory_ibm_imm_temp(section: Mapping[str, SensorTemperature]) -> None:
    assert list(discover_ibm_imm_temp(section)) == [
        Service(item="PCH Temp"),
        Service(item="Ambient Temp"),
        Service(item="PCI Riser 1 Temp"),
        Service(item="CPU1 VR Temp"),
        Service(item="CPU2 VR Temp"),
        Service(item="DIMM AB VR Temp"),
        Service(item="DIMM CD VR Temp"),
        Service(item="DIMM EF VR Temp"),
        Service(item="DIMM GH VR Temp"),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", [], id="Item missing in data"),
        pytest.param(
            "DIMM AB VR Temp",
            [
                Metric("temp", 24.0, levels=(95.0, 100.0)),
                Result(state=State.OK, summary="Temperature: 24.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="Item OK in data",
        ),
        pytest.param(
            "CPU1 VR Temp",
            [
                Metric("temp", 129.0, levels=(95.0, 100.0)),
                Result(
                    state=State.CRIT,
                    summary="Temperature: 129.0 °C (warn/crit at 95.0 °C/100.0 °C)",
                ),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="Item CRIT in data",
        ),
        pytest.param(
            "Ambient Temp",
            [
                Metric("temp", 17.0, levels=(43.0, 47.0)),
                Result(state=State.OK, summary="Temperature: 17.0 °C"),
                Result(
                    state=State.OK,
                    notice="Configuration: prefer user levels over device levels (used device levels)",
                ),
            ],
            id="Item in data with empty string",
        ),
    ],
)
def test_check_ibm_imm_temp(
    section: Mapping[str, SensorTemperature], item: str, expected_output: Sequence[object]
) -> None:
    assert list(_check_ibm_imm_temp(item, {}, section, {})) == expected_output
