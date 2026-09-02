#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import pytest

from cmk.agent_based.v2 import StringTable
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
    assert discover_intel_true_scale_fans(parse_intel_true_scale_fans(STRING_TABLE)) == [
        ("201", None),
        ("202", None),
        ("203", None),
        ("205", None),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        pytest.param(
            "201",
            [(0, "Operational status: online"), (0, "Speed status: normal")],
            id="online_and_normal",
        ),
        pytest.param(
            "202",
            [(0, "Operational status: operational"), (2, "Speed status: low")],
            id="operational_and_low",
        ),
        pytest.param(
            "203",
            [(2, "Operational status: failed"), (2, "Speed status: high")],
            id="failed_and_high",
        ),
        pytest.param(
            "204",
            [(1, "Operational status: offline"), (0, "Speed status: normal")],
            id="offline_stays_checkable",
        ),
        pytest.param(
            "205",
            [(0, "Operational status: operational"), (3, "Speed status: unknown")],
            id="operational_and_unknown_speed",
        ),
        pytest.param("101", [], id="unknown_item"),
    ],
)
def test_check_intel_true_scale_fans(item: str, expected_results: list[tuple[int, str]]) -> None:
    assert (
        list(check_intel_true_scale_fans(item, None, parse_intel_true_scale_fans(STRING_TABLE)))
        == expected_results
    )
