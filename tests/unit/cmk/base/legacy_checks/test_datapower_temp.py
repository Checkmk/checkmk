#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.datapower_temp import (
    check_datapower_temp,
    inventory_datapower_temp,
    parse_datapower_temp,
)
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import CheckResult

_STRING_TABLE = [
    ["Temperature CPU1", "50.0", "65.0", "1", "70.0"],
    ["Temperature CPU2", "40.0", "35.0", "1", "50.0"],
    ["Temperature CPU3", "70.0", "", "1", "60.0"],
    ["Temperature CPU4", "20.0", "65.0", "9", "70.0"],
    ["Temperature CPU5", "20.0", "65.0", "8", "70.0"],
]


def test_discover_datapower_temp() -> None:
    assert list(inventory_datapower_temp(parse_datapower_temp(_STRING_TABLE))) == [
        ("CPU1", {}),
        ("CPU2", {}),
        ("CPU3", {}),
        ("CPU4", {}),
        ("CPU5", {}),
    ]


@pytest.mark.parametrize(
    "item, expected_result",
    [
        pytest.param(
            "CPU1",
            [0, "50.0 °C", [("temp", 50.0, 65.0, 70.0)]],
            id="normal",
        ),
        pytest.param(
            "CPU2",
            [1, "40.0 °C (device warn/crit at 35.0/50.0 °C)", [("temp", 40.0, 35.0, 50.0)]],
            id="WARN",
        ),
        pytest.param(
            "CPU3",
            [0, "70.0 °C", [("temp", 70.0, None, None)]],
            id="missing dev_warn_level",
        ),
        pytest.param(
            "CPU4",
            [3, "device status: noReading"],
            id="no reading",
        ),
        pytest.param(
            "CPU5",
            [2, "device status: failure"],
            id="failure",
        ),
    ],
)
def test_check_datapower_temp(
    item: str,
    expected_result: CheckResult,
) -> None:
    assert (
        list(
            check_datapower_temp(
                item=item,
                params={},
                info=parse_datapower_temp(_STRING_TABLE),
            )
        )
        == expected_result
    )
