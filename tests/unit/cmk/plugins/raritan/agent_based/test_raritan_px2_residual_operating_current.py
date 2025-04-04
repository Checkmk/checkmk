#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringByteTable
from cmk.plugins.raritan.agent_based.raritan_px2_residual_operating_current import (
    check_raritan_px2_residual_current,
    discover_raritan_px2_residual_current,
    Params,
    parse_raritan_inlet_sensors,
)

STRING_TABLE: Sequence[StringByteTable] = [
    [
        [
            "",
            "I1",
            "",
            "28",
            "4",
            "380-415V",
            "32A",
            "",
            "",
            [191, 0, 2, 96, 0, 0],
            [159, 0, 0, 96, 0, 0],
            "IEC 60309 3P+N+E 6h 32A",
            "1",
        ]
    ],
    [
        ["1", "1", "1", "2", "1", "0", "0", [0]],
        ["3", "26", "2", "9", "0", "10", "5", [0]],
        ["4", "1", "390", "1", "0", "0", "0", [0]],
        ["26", "1", "0.31", "8", "1", "0", "0", [0]],
    ],
    [
        ["1.1", "1", "1", "2", "1", "256", "208", [48]],
        ["1.4", "1", "390", "1", "0", "440", "427", [240]],
        ["3.26", "1", "0.02", "1", "0", "254", "247", [0]],
    ],
]


def test_discover_raritan_px2_residual_operating_current() -> None:
    section = parse_raritan_inlet_sensors(STRING_TABLE)
    assert section
    assert list(discover_raritan_px2_residual_current(section)) == [
        Service(item="Summary"),
        Service(item="Phase 3"),
    ]


@pytest.mark.parametrize(
    "item, params, string_table, expected",
    [
        pytest.param(
            "Summary",
            Params(warn_missing_levels=False, warn_missing_data=False),
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Residual Current: 31.0 mA"),
                Metric("residual_current", 0.031),
                Result(state=State.OK, notice="Residual Current Percentage: 31.00%"),
                Metric("residual_current_percentage", 31.0),
                Result(state=State.OK, notice="Missing warn/crit levels!"),
            ],
            id="all_is_OK",
        ),
        pytest.param(
            "Summary",
            Params(warn_missing_levels=True, warn_missing_data=True),
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Residual Current: 31.0 mA"),
                Metric("residual_current", 0.031),
                Result(state=State.OK, notice="Residual Current Percentage: 31.00%"),
                Metric("residual_current_percentage", 31.0),
                Result(state=State.WARN, summary="Missing warn/crit levels!"),
            ],
            id="warn_for_missing_levels",
        ),
        pytest.param(
            "Phase 3",
            Params(
                warn_missing_levels=True,
                warn_missing_data=True,
                residual_levels=("fixed", (0.01, 0.03)),
            ),
            STRING_TABLE,
            [
                Result(
                    state=State.WARN,
                    summary="Residual Current: 20.0 mA (warn/crit at 10.0 mA/30.0 mA)",
                ),
                Metric("residual_current", 0.02, levels=(0.01, 0.03)),
            ],
            id="user_levels_defined - WARN",
        ),
        pytest.param(
            "Phase 3",
            Params(
                warn_missing_levels=True,
                warn_missing_data=True,
                residual_levels=("fixed", (0.0, 0.01)),
            ),
            STRING_TABLE,
            [
                Result(
                    state=State.CRIT,
                    summary="Residual Current: 20.0 mA (warn/crit at 0.0 mA/10.0 mA)",
                ),
                Metric("residual_current", 0.02, levels=(0.0, 0.01)),
            ],
            id="user_levels_defined - CRIT",
        ),
    ],
)
def test_check_raritan_px2_residual_operating_current(
    string_table: Sequence[StringByteTable],
    item: str,
    params: Params,
    expected: CheckResult,
) -> None:
    section = parse_raritan_inlet_sensors(string_table)
    assert section
    assert list(check_raritan_px2_residual_current(item, params, section)) == expected
