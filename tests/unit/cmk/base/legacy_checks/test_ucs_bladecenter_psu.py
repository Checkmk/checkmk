#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.ucs_bladecenter_psu import (
    check_ucs_bladecenter_psu,
    inventory_ucs_bladecenter_psu,
    ucs_bladecenter_psu_parse,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-A/psu-2/input-stats",
                    "Current 0.625000",
                    "PowerAvg 142.333344",
                    "Voltage 228.000000",
                ],
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-A/psu-1/input-stats",
                    "Current 0.562500",
                    "PowerAvg 132.431259",
                    "Voltage 236.000000",
                ],
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-B/psu-2/input-stats",
                    "Current 0.625000",
                    "PowerAvg 142.670456",
                    "Voltage 228.500000",
                ],
                [
                    "equipmentPsuStats",
                    "Dn sys/chassis-1/psu-1/stats",
                    "AmbientTemp 17.000000",
                    "Output12vAvg 12.008000",
                    "Output3v3Avg 3.336000",
                ],
            ],
            [("Chassis 1 Module 1", {})],
        ),
    ],
)
def test_inventory_ucs_bladecenter_psu(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for ucs_bladecenter_psu check."""
    parsed = ucs_bladecenter_psu_parse(info)
    result = list(inventory_ucs_bladecenter_psu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "Chassis 1 Module 1",
            {
                "levels_3v_upper": (3.4, 3.45),
                "levels_12v_upper": (12.1, 12.2),
                "levels_3v_lower": (3.25, 3.2),
                "levels_12v_lower": (11.9, 11.8),
            },
            [
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-A/psu-2/input-stats",
                    "Current 0.625000",
                    "PowerAvg 142.333344",
                    "Voltage 228.000000",
                ],
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-A/psu-1/input-stats",
                    "Current 0.562500",
                    "PowerAvg 132.431259",
                    "Voltage 236.000000",
                ],
                [
                    "equipmentPsuInputStats",
                    "Dn sys/switch-B/psu-2/input-stats",
                    "Current 0.625000",
                    "PowerAvg 142.670456",
                    "Voltage 228.500000",
                ],
                [
                    "equipmentPsuStats",
                    "Dn sys/chassis-1/psu-1/stats",
                    "AmbientTemp 17.000000",
                    "Output12vAvg 12.008000",
                    "Output3v3Avg 3.336000",
                ],
            ],
            [
                (0, "Output 3.3V-Average: 3.34 V", [("3_3v", 3.336, 3.4, 3.45)]),
                (0, "Output 12V-Average: 12.01 V", [("12v", 12.008, 12.1, 12.2)]),
            ],
        ),
    ],
)
def test_check_ucs_bladecenter_psu(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for ucs_bladecenter_psu check."""
    parsed = ucs_bladecenter_psu_parse(info)
    result = list(check_ucs_bladecenter_psu(item, params, parsed))
    assert result == expected_results
