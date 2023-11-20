#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.base.legacy_checks.ibm_imm_temp import check_ibm_imm_temp, inventory_ibm_imm_temp

STRING_TABLE = [
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


def test_inventory_ibm_imm_temp() -> None:
    assert list(inventory_ibm_imm_temp(STRING_TABLE)) == [
        ("PCH Temp", {}),
        ("Ambient Temp", {}),
        ("PCI Riser 1 Temp", {}),
        ("CPU1 VR Temp", {}),
        ("CPU2 VR Temp", {}),
        ("DIMM AB VR Temp", {}),
        ("DIMM CD VR Temp", {}),
        ("DIMM EF VR Temp", {}),
        ("DIMM GH VR Temp", {}),
    ]


@pytest.mark.parametrize(
    "item, expected_output",
    [
        pytest.param("missing", None, id="Item missing in data"),
        pytest.param(
            "DIMM AB VR Temp",
            (0, "24.0 °C", [("temp", 24.0, 95.0, 100.0)]),
            id="Item OK in data",
        ),
        pytest.param(
            "CPU1 VR Temp",
            (
                2,
                "129.0 °C (device warn/crit at 95.0/100.0 °C) (device warn/crit below 0.0/0.0 °C)",
                [("temp", 129.0, 95.0, 100.0)],
            ),
            id="Item CRIT in data",
        ),
        pytest.param(
            "Ambient Temp",
            (0, "17.0 °C", [("temp", 17.0, 43.0, 47.0)]),
            id="Item in data with empty string",
        ),
    ],
)
def test_check_ibm_imm_temp(item: str, expected_output: Sequence[object]) -> None:
    assert check_ibm_imm_temp(item, None, STRING_TABLE) == expected_output
