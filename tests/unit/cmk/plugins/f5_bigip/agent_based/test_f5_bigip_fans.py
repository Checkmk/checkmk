#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_fans import (
    check_f5_bigip_fans,
    discover_f5_bigip_fans,
    FanParams,
    parse_f5_bigip_fans,
)

_STRING_TABLE = [
    [
        ["1", "1", "15574"],
        ["2", "1", "16266"],
        ["3", "1", "15913"],
        ["4", "1", "16266"],
        ["5", "0", "0"],
        ["6", "1", "0"],
    ],
    [
        ["1/cpu1", "4715"],
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            _STRING_TABLE,
            [
                Service(item="Chassis 1"),
                Service(item="Chassis 2"),
                Service(item="Chassis 3"),
                Service(item="Chassis 4"),
                Service(item="Chassis 5"),
                Service(item="Chassis 6"),
                Service(item="Processor 1/cpu1"),
            ],
        ),
    ],
)
def test_discover_f5_bigip_fans(
    string_table: Sequence[StringTable], expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for f5_bigip_fans check."""
    section = parse_f5_bigip_fans(string_table)
    assert list(discover_f5_bigip_fans(section)) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        pytest.param(
            "Chassis 1",
            FanParams(lower=(2000, 500)),
            _STRING_TABLE,
            [Result(state=State.OK, summary="Speed: 15574 RPM")],
            id="chassis fan spinning",
        ),
        pytest.param(
            "Chassis 5",
            FanParams(lower=(2000, 500)),
            _STRING_TABLE,
            [
                Result(
                    state=State.CRIT,
                    summary="Speed: 0 RPM (warn/crit below 2000 RPM/500 RPM)",
                )
            ],
            id="chassis fan stopped and reporting bad status",
        ),
        pytest.param(
            "Chassis 6",
            FanParams(lower=(2000, 500)),
            _STRING_TABLE,
            [Result(state=State.OK, summary="Fan Status: OK")],
            id="chassis fan without speed but with good status",
        ),
        pytest.param(
            "Processor 1/cpu1",
            FanParams(lower=(2000, 500)),
            _STRING_TABLE,
            [Result(state=State.OK, summary="Speed: 4715 RPM")],
            id="cpu fan",
        ),
        pytest.param(
            "Chassis 1",
            FanParams(lower=(2000, 500), output_metrics=True),
            _STRING_TABLE,
            [
                Result(state=State.OK, summary="Speed: 15574 RPM"),
                Metric("fan", 15574.0, levels=(None, None)),
            ],
            id="metrics enabled",
        ),
        pytest.param(
            "Chassis 7",
            FanParams(lower=(2000, 500)),
            _STRING_TABLE,
            [],
            id="unknown item",
        ),
    ],
)
def test_check_f5_bigip_fans(
    item: str,
    params: FanParams,
    string_table: Sequence[StringTable],
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for f5_bigip_fans check."""
    section = parse_f5_bigip_fans(string_table)
    assert list(check_f5_bigip_fans(item, params, section)) == expected_results
