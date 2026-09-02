#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.intel_true_scale_fans import (
    check_intel_true_scale_fans,
    discover_intel_true_scale_fans,
    parse_intel_true_scale_fans,
)

# synthetic data covering every operational and speed state
STRING_TABLE: StringTable = [
    ["Fan 201", "1", "2"],
    ["Fan 202", "2", "1"],
    ["Fan 203", "3", "3"],
    ["Fan 204", "4", "2"],
    ["Fan 205", "2", "4"],
]


def test_discover_intel_true_scale_fans_strips_prefix_and_skips_offline() -> None:
    assert list(discover_intel_true_scale_fans(parse_intel_true_scale_fans(STRING_TABLE))) == [
        Service(item="201"),
        Service(item="202"),
        Service(item="203"),
        Service(item="205"),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        pytest.param(
            "201",
            [
                Result(state=State.OK, summary="Operational status: online"),
                Result(state=State.OK, summary="Speed status: normal"),
            ],
            id="online_and_normal",
        ),
        pytest.param(
            "202",
            [
                Result(state=State.OK, summary="Operational status: operational"),
                Result(state=State.CRIT, summary="Speed status: low"),
            ],
            id="operational_and_low",
        ),
        pytest.param(
            "203",
            [
                Result(state=State.CRIT, summary="Operational status: failed"),
                Result(state=State.CRIT, summary="Speed status: high"),
            ],
            id="failed_and_high",
        ),
        pytest.param(
            "204",
            [
                Result(state=State.WARN, summary="Operational status: offline"),
                Result(state=State.OK, summary="Speed status: normal"),
            ],
            id="offline_stays_checkable",
        ),
        pytest.param(
            "205",
            [
                Result(state=State.OK, summary="Operational status: operational"),
                Result(state=State.UNKNOWN, summary="Speed status: unknown"),
            ],
            id="operational_and_unknown_speed",
        ),
        pytest.param("101", [], id="unknown_item"),
    ],
)
def test_check_intel_true_scale_fans(item: str, expected_results: list[Result]) -> None:
    assert (
        list(check_intel_true_scale_fans(item, parse_intel_true_scale_fans(STRING_TABLE)))
        == expected_results
    )
