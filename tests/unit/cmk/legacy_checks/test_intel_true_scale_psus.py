#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.intel_true_scale_psus import (
    check_intel_true_scale_psus,
    discover_intel_true_scale_psus,
    parse_intel_true_scale_psus,
)

# synthetic data covering every operational state and every input source
STRING_TABLE: StringTable = [
    ["Power Supply 201", "6", "1", "12", "150"],
    ["Power Supply 202", "3", "2", "11.2", "140"],
    ["Power Supply 203", "8", "1", "0", "0"],
    ["Power Supply 204", "2", "3", "0", "0"],
    ["Power Supply 205", "4", "0", "10", "120"],
    ["Power Supply 206", "1", "4", "12", "130"],
    ["Power Supply 207", "5", "1", "12", "0"],
    ["Power Supply 208", "7", "1", "12", "160"],
]


def test_discover_intel_true_scale_psus_skips_absent_and_disabled() -> None:
    assert list(discover_intel_true_scale_psus(parse_intel_true_scale_psus(STRING_TABLE))) == [
        ("201", {}),
        ("202", {}),
        ("205", {}),
        ("206", {}),
        ("207", {}),
        ("208", {}),
    ]


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        pytest.param(
            "206",
            {},
            [
                (3, "Operational status: unknown, Source: unknown"),
                (0, "Voltage: 12.0 V", [("voltage", 12.0, None, None)]),
                (0, "Power: 130.0 W", [("power", 130.0, None, None)]),
            ],
            id="unknown",
        ),
        pytest.param(
            "204",
            {},
            [
                (3, "Operational status: disabled, Source: none"),
                (0, "Voltage: 0.0 V", [("voltage", 0.0, None, None)]),
                (0, "Power: 0.0 W", [("power", 0.0, None, None)]),
            ],
            id="disabled",
        ),
        pytest.param(
            "202",
            {},
            [
                (2, "Operational status: failed, Source: dc line"),
                (0, "Voltage: 11.2 V", [("voltage", 11.2, None, None)]),
                (0, "Power: 140.0 W", [("power", 140.0, None, None)]),
            ],
            id="failed",
        ),
        pytest.param(
            "205",
            {},
            [
                (1, "Operational status: warning, Source: invalid"),
                (0, "Voltage: 10.0 V", [("voltage", 10.0, None, None)]),
                (0, "Power: 120.0 W", [("power", 120.0, None, None)]),
            ],
            id="warning",
        ),
        pytest.param(
            "207",
            {},
            [
                (0, "Operational status: standby, Source: ac line"),
                (0, "Voltage: 12.0 V", [("voltage", 12.0, None, None)]),
                (0, "Power: 0.0 W", [("power", 0.0, None, None)]),
            ],
            id="standby",
        ),
        pytest.param(
            "201",
            {},
            [
                (0, "Operational status: engaged, Source: ac line"),
                (0, "Voltage: 12.0 V", [("voltage", 12.0, None, None)]),
                (0, "Power: 150.0 W", [("power", 150.0, None, None)]),
            ],
            id="engaged",
        ),
        pytest.param(
            "208",
            {},
            [
                (0, "Operational status: redundant, Source: ac line"),
                (0, "Voltage: 12.0 V", [("voltage", 12.0, None, None)]),
                (0, "Power: 160.0 W", [("power", 160.0, None, None)]),
            ],
            id="redundant",
        ),
        pytest.param(
            "203",
            {},
            [
                (3, "Operational status: not present, Source: ac line"),
                (0, "Voltage: 0.0 V", [("voltage", 0.0, None, None)]),
                (0, "Power: 0.0 W", [("power", 0.0, None, None)]),
            ],
            id="not_present_stays_checkable",
        ),
        pytest.param(
            "202",
            {"voltage": (11.5, 11.0)},
            [
                (2, "Operational status: failed, Source: dc line"),
                (
                    1,
                    "Voltage: 11.2 V (warn/crit below 11.5 V/11.0 V)",
                    [("voltage", 11.2, None, None)],
                ),
                (0, "Power: 140.0 W", [("power", 140.0, None, None)]),
            ],
            id="voltage_warn_is_a_lower_bound",
        ),
        pytest.param(
            "205",
            {"voltage": (11.5, 11.0)},
            [
                (1, "Operational status: warning, Source: invalid"),
                (
                    2,
                    "Voltage: 10.0 V (warn/crit below 11.5 V/11.0 V)",
                    [("voltage", 10.0, None, None)],
                ),
                (0, "Power: 120.0 W", [("power", 120.0, None, None)]),
            ],
            id="voltage_crit_is_a_lower_bound",
        ),
        pytest.param(
            "201",
            {"power": (100.0, 200.0)},
            [
                (0, "Operational status: engaged, Source: ac line"),
                (0, "Voltage: 12.0 V", [("voltage", 12.0, None, None)]),
                (
                    1,
                    "Power: 150.0 W (warn/crit at 100.0 W/200.0 W)",
                    [("power", 150.0, 100.0, 200.0)],
                ),
            ],
            id="power_levels_are_upper_bounds",
        ),
        pytest.param("999", {}, [], id="unknown_item"),
    ],
)
def test_check_intel_true_scale_psus(
    item: str,
    params: Mapping[str, object],
    expected_results: list[object],
) -> None:
    assert (
        list(check_intel_true_scale_psus(item, params, parse_intel_true_scale_psus(STRING_TABLE)))
        == expected_results
    )
