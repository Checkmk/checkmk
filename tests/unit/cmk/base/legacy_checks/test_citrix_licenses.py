#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.citrix_licenses import (
    check_citrix_licenses,
    discover_citrix_licenses,
    parse_citrix_licenses,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [
                ("CEHV_ENT_CCS", {}),
                ("MPS_ENT_CCU", {}),
                ("PVSD_STD_CCS", {}),
                ("PVS_STD_CCS", {}),
                ("XDS_ENT_CCS", {}),
                ("XDT_ENT_UD", {}),
            ],
        ),
    ],
)
def test_discover_citrix_licenses(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for citrix_licenses check."""
    parsed = parse_citrix_licenses(string_table)
    result = list(discover_citrix_licenses(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "CEHV_ENT_CCS",
            {"levels": ("crit_on_all", None)},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [(0, "used 0 out of 22 licenses", [("licenses", 0, 22, 22, 0, 22)])],
        ),
        (
            "MPS_ENT_CCU",
            {"levels": ("crit_on_all", None)},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [(0, "used 1658 out of 2182 licenses", [("licenses", 1658, 2182, 2182, 0, 2182)])],
        ),
        (
            "PVSD_STD_CCS",
            {"levels": ("percentage", (10.0, 0.0))},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [
                (
                    1,
                    "used 40 out of 42 licenses (warn/crit at 37/42)",
                    [("licenses", 40, 37.800000000000004, 42, 0, 42)],
                )
            ],
        ),
        (
            "PVS_STD_CCS",
            {"levels": ("absolute", (5, 0))},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [
                (
                    1,
                    "used 99 out of 102 licenses (warn/crit at 97/102)",
                    [("licenses", 99, 97, 102, 0, 102)],
                )
            ],
        ),
        (
            "XDS_ENT_CCS",
            {"levels": ("crit_on_all", None)},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [(0, "used 0 out of 22 licenses", [("licenses", 0, 22, 22, 0, 22)])],
        ),
        (
            "XDT_ENT_UD",
            {"levels": ("crit_on_all", None)},
            [
                ["PVS_STD_CCS", "80", "90"],
                ["PVS_STD_CCS", "22", "9"],
                ["CEHV_ENT_CCS", "22", "0"],
                ["MPS_ENT_CCU", "2160", "1636"],
                ["MPS_ENT_CCU", "22", "22"],
                ["XDT_ENT_UD", "22", "23"],
                ["XDS_ENT_CCS", "22", "0"],
                ["PVSD_STD_CCS", "42", "40"],
            ],
            [
                (
                    2,
                    "used 23 licenses, but you have only 22 (warn/crit at 22/22)",
                    [("licenses", 23, 22, 22, 0, 22)],
                )
            ],
        ),
    ],
)
def test_check_citrix_licenses(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for citrix_licenses check."""
    parsed = parse_citrix_licenses(string_table)
    result = list(check_citrix_licenses(item, params, parsed))
    assert result == expected_results
