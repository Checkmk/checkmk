#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.check_legacy_includes.quanta import parse_quanta
from cmk.base.legacy_checks.quanta_temperature import (
    check_quanta_temperature,
    discover_quanta_temperature,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [
                ("Temp_CPU0_Inlet", {}),
                ("Temp_CPU1_Inlet", {}),
                ("Temp_DIMM_AB", {}),
                ("Temp_DIMM_CD", {}),
                ("Temp_PCI1_Outlet", {}),
            ],
        ),
    ],
)
def test_discover_quanta_temperature(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for quanta_temperature check."""

    parsed = parse_quanta(info)
    result = list(discover_quanta_temperature(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "Temp_CPU0_Inlet",
            {},
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [(0, "37.0 °C", [("temp", 37.0, 70.0, 75.0)])],
        ),
        (
            "Temp_CPU1_Inlet",
            {},
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [(0, "37.0 °C", [("temp", 37.0, 75.0, 75.0)])],
        ),
        (
            "Temp_DIMM_AB",
            {},
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [(1, "Status: other")],
        ),
        (
            "Temp_DIMM_CD",
            {},
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [(3, "Status: unknown")],
        ),
        (
            "Temp_PCI1_Outlet",
            {},
            [
                [
                    ["1", "3", "Temp_PCI1_Outlet\x01", "41", "85", "80", "-99", "-99"],
                    ["2", "3", "Temp_CPU0_Inlet", "37", "75", "70", "-99", "-99"],
                    ["2", "3", "Temp_CPU1_Inlet", "37", "75", "-99", "-99", "-99"],
                    ["7", "1", "Temp_DIMM_AB", "-99", "85", "84", "-99", "-99"],
                    ["7", "2", "Temp_DIMM_CD", "-99", "85", "84", "95", "100"],
                ]
            ],
            [(0, "41.0 °C", [("temp", 41.0, 80.0, 85.0)])],
        ),
    ],
)
def test_check_quanta_temperature(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for quanta_temperature check."""

    parsed = parse_quanta(info)
    result = list(check_quanta_temperature(item, params, parsed))
    assert result == expected_results
