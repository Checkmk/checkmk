#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.base.legacy_checks.ucs_bladecenter_fans import (
    check_ucs_bladecenter_fans,
    discover_ucs_bladecenter_fans,
    parse_ucs_bladecenter_fans,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    "equipmentNetworkElementFanStats",
                    "Dn sys/switch-A/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 8542",
                ],
                [
                    "equipmentFanModuleStats",
                    "Dn sys/chassis-2/fan-module-1-1/stats",
                    "AmbientTemp 29.000000",
                ],
                [
                    "equipmentFan",
                    "Dn sys/chassis-1/fan-module-1-1/fan-1",
                    "Model N20-FAN5",
                    "OperState operable",
                ],
                [
                    "equipmentFanStats",
                    "Dn sys/chassis-2/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 3652",
                ],
            ],
            [Service(item="Chassis 2"), Service(item="Switch A")],
        ),
    ],
)
def test_inventory_ucs_bladecenter_fans(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for ucs_bladecenter_fans check."""
    parsed = parse_ucs_bladecenter_fans(string_table)
    result = list(discover_ucs_bladecenter_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "Chassis 2",
            [
                [
                    "equipmentNetworkElementFanStats",
                    "Dn sys/switch-A/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 8542",
                ],
                [
                    "equipmentFanModuleStats",
                    "Dn sys/chassis-2/fan-module-1-1/stats",
                    "AmbientTemp 29.000000",
                ],
                [
                    "equipmentFan",
                    "Dn sys/chassis-1/fan-module-1-1/fan-1",
                    "Model N20-FAN5",
                    "OperState operable",
                ],
                [
                    "equipmentFanStats",
                    "Dn sys/chassis-2/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 3652",
                ],
            ],
            [Result(state=State.UNKNOWN, summary="Fan statistics not available")],
        ),
        (
            "Switch A",
            [
                [
                    "equipmentNetworkElementFanStats",
                    "Dn sys/switch-A/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 8542",
                ],
                [
                    "equipmentFanModuleStats",
                    "Dn sys/chassis-2/fan-module-1-1/stats",
                    "AmbientTemp 29.000000",
                ],
                [
                    "equipmentFan",
                    "Dn sys/chassis-1/fan-module-1-1/fan-1",
                    "Model N20-FAN5",
                    "OperState operable",
                ],
                [
                    "equipmentFanStats",
                    "Dn sys/chassis-2/fan-module-1-1/fan-1/stats",
                    "SpeedAvg 3652",
                ],
            ],
            [Result(state=State.UNKNOWN, summary="Fan statistics not available")],
        ),
    ],
)
def test_check_ucs_bladecenter_fans(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    """Test check function for ucs_bladecenter_fans check."""
    parsed = parse_ucs_bladecenter_fans(string_table)
    result = list(check_ucs_bladecenter_fans(item, parsed))
    assert result == expected_results
