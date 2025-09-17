#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.teracom_tcw241_analog import (
    check_tcw241_analog,
    discover_teracom_tcw241_analog,
    parse_tcw241_analog,
)


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [["Tank_Level", "80000", "10000"]],
                [["Motor_Temp", "70000", "37000"]],
                [["Analog Input 3", "60000", "0"]],
                [["Analog Input 4", "60000", "0"]],
                [["48163", "39158", "33", "34"]],
            ],
            [("1", {}), ("2", {})],
        ),
    ],
)
def test_discover_teracom_tcw241_analog(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for teracom_tcw241_analog check."""
    parsed = parse_tcw241_analog(info)
    result = list(discover_teracom_tcw241_analog(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "2",
            {},
            [
                [["Tank_Level", "80000", "10000"]],
                [["Motor_Temp", "70000", "37000"]],
                [["Analog Input 3", "60000", "0"]],
                [["Analog Input 4", "60000", "0"]],
                [["48163", "39158", "33", "34"]],
            ],
            [
                (
                    1,
                    "[Motor_Temp]: 39.16 V (warn/crit at 37.00 V/70.00 V)",
                    [("voltage", 39.158, 37.0, 70.0)],
                )
            ],
        ),
        (
            "1",
            {},
            [
                [["Tank_Level", "80000", "10000"]],
                [["Motor_Temp", "70000", "37000"]],
                [["Analog Input 3", "60000", "0"]],
                [["Analog Input 4", "60000", "0"]],
                [["48163", "39158", "33", "34"]],
            ],
            [
                (
                    1,
                    "[Tank_Level]: 48.16 V (warn/crit at 10.00 V/80.00 V)",
                    [("voltage", 48.163, 10.0, 80.0)],
                )
            ],
        ),
    ],
)
def test_check_teracom_tcw241_analog(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for teracom_tcw241_analog check."""
    parsed = parse_tcw241_analog(info)
    result = list(check_tcw241_analog(item, params, parsed))
    assert result == expected_results
