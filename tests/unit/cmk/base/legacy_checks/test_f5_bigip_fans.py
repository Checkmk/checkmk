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
from cmk.base.legacy_checks.f5_bigip_fans import (
    check_f5_bigip_fans,
    discover_f5_bigip_fans,
    parse_f5_bigip_fans,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    ["1", "1", "15574"],
                    ["2", "1", "16266"],
                    ["3", "1", "15913"],
                    ["4", "1", "16266"],
                    ["5", "0", "0"],
                    ["6", "1", "0"],
                ],
                [],
            ],
            [
                ("Chassis 1", {}),
                ("Chassis 2", {}),
                ("Chassis 3", {}),
                ("Chassis 4", {}),
                ("Chassis 5", {}),
                ("Chassis 6", {}),
            ],
        ),
    ],
)
def test_discover_f5_bigip_fans(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for f5_bigip_fans check."""
    parsed = parse_f5_bigip_fans(string_table)
    result = list(discover_f5_bigip_fans(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "Chassis 1",
            {"lower": (2000, 500)},
            [
                [
                    ["1", "1", "15574"],
                    ["2", "1", "16266"],
                    ["3", "1", "15913"],
                    ["4", "1", "16266"],
                    ["5", "0", "0"],
                    ["6", "1", "0"],
                ],
                [],
            ],
            [(0, "Speed: 15574 RPM", [])],
        ),
        (
            "Chassis 5",
            {"lower": (2000, 500)},
            [
                [
                    ["1", "1", "15574"],
                    ["2", "1", "16266"],
                    ["3", "1", "15913"],
                    ["4", "1", "16266"],
                    ["5", "0", "0"],
                    ["6", "1", "0"],
                ],
                [],
            ],
            [(2, "Speed: 0 RPM (warn/crit below 2000 RPM/500 RPM)", [])],
        ),
        (
            "Chassis 6",
            {"lower": (2000, 500)},
            [
                [
                    ["1", "1", "15574"],
                    ["2", "1", "16266"],
                    ["3", "1", "15913"],
                    ["4", "1", "16266"],
                    ["5", "0", "0"],
                    ["6", "1", "0"],
                ],
                [],
            ],
            [(0, "Fan Status: OK")],
        ),
    ],
)
def test_check_f5_bigip_fans(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for f5_bigip_fans check."""
    parsed = parse_f5_bigip_fans(string_table)
    result = list(check_f5_bigip_fans(item, params, parsed))
    assert result == expected_results
