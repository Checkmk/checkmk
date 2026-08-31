#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import DiscoveryResult, Metric, Result, Service, State, StringTable
from cmk.legacy_checks.fsc_fans import check_fsc_fans, discover_fsc_fans, parse_fsc_fans

_STRING_TABLE = [
    ["NULL", "NULL"],  # invalid fan entry (filtered out)
    ["FAN1 SYS", "4140"],
]


@pytest.mark.parametrize(
    "string_table, expected_section",
    [
        pytest.param(_STRING_TABLE, {"FAN1 SYS": 4140}, id="invalid rpm value is skipped"),
        pytest.param(
            [["FAN1", "not_a_number"], ["FAN2", ""], ["FAN3", "1500"]],
            {"FAN3": 1500},
            id="only parsable rpm values are kept",
        ),
    ],
)
def test_parse_fsc_fans(string_table: StringTable, expected_section: Mapping[str, int]) -> None:
    assert parse_fsc_fans(string_table) == expected_section


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        pytest.param(_STRING_TABLE, [Service(item="FAN1 SYS")], id="one fan"),
        pytest.param([], [], id="no data"),
        pytest.param(
            [["FAN1 SYS", "4140"], ["FAN2 SYS", "3800"], ["FAN3 CPU", "4500"], ["NULL", "NULL"]],
            [Service(item="FAN1 SYS"), Service(item="FAN2 SYS"), Service(item="FAN3 CPU")],
            id="multiple fans",
        ),
    ],
)
def test_discover_fsc_fans(
    string_table: StringTable, expected_discoveries: DiscoveryResult
) -> None:
    assert list(discover_fsc_fans(parse_fsc_fans(string_table))) == expected_discoveries


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        pytest.param(
            "FAN1 SYS",
            {"lower": (2000, 1000)},
            [Result(state=State.OK, summary="Speed: 4140 RPM")],
            id="speed above lower levels",
        ),
        pytest.param(
            "FAN1 SYS",
            {"lower": (5000, 4000)},
            [
                Result(
                    state=State.WARN,
                    summary="Speed: 4140 RPM (warn/crit below 5000 RPM/4000 RPM)",
                )
            ],
            id="speed below warn level",
        ),
        pytest.param(
            "FAN1 SYS",
            {"lower": (6000, 5000)},
            [
                Result(
                    state=State.CRIT,
                    summary="Speed: 4140 RPM (warn/crit below 6000 RPM/5000 RPM)",
                )
            ],
            id="speed below crit level",
        ),
        pytest.param(
            "FAN1 SYS",
            {"lower": (2000, 1000), "output_metrics": True},
            [
                Result(state=State.OK, summary="Speed: 4140 RPM"),
                Metric("fan", 4140.0),
            ],
            id="metrics enabled",
        ),
        pytest.param("NONEXISTENT", {"lower": (2000, 1000)}, [], id="unknown item"),
    ],
)
def test_check_fsc_fans(
    item: str, params: Mapping[str, object], expected_results: Sequence[object]
) -> None:
    assert list(check_fsc_fans(item, params, parse_fsc_fans(_STRING_TABLE))) == expected_results
