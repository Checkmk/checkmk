#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
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
        Service(item="201"),
        Service(item="202"),
        Service(item="205"),
        Service(item="206"),
        Service(item="207"),
        Service(item="208"),
    ]


@pytest.mark.parametrize(
    "item, params, expected_results",
    [
        pytest.param(
            "206",
            {},
            [
                Result(state=State.UNKNOWN, summary="Operational status: unknown, Source: unknown"),
                Result(state=State.OK, summary="Voltage: 12.0 V"),
                Metric("voltage", 12.0),
                Result(state=State.OK, summary="Power: 130.0 W"),
                Metric("power", 130.0),
            ],
            id="unknown",
        ),
        pytest.param(
            "204",
            {},
            [
                Result(state=State.UNKNOWN, summary="Operational status: disabled, Source: none"),
                Result(state=State.OK, summary="Voltage: 0.0 V"),
                Metric("voltage", 0.0),
                Result(state=State.OK, summary="Power: 0.0 W"),
                Metric("power", 0.0),
            ],
            id="disabled",
        ),
        pytest.param(
            "202",
            {},
            [
                Result(state=State.CRIT, summary="Operational status: failed, Source: dc line"),
                Result(state=State.OK, summary="Voltage: 11.2 V"),
                Metric("voltage", 11.2),
                Result(state=State.OK, summary="Power: 140.0 W"),
                Metric("power", 140.0),
            ],
            id="failed",
        ),
        pytest.param(
            "205",
            {},
            [
                Result(state=State.WARN, summary="Operational status: warning, Source: invalid"),
                Result(state=State.OK, summary="Voltage: 10.0 V"),
                Metric("voltage", 10.0),
                Result(state=State.OK, summary="Power: 120.0 W"),
                Metric("power", 120.0),
            ],
            id="warning",
        ),
        pytest.param(
            "207",
            {},
            [
                Result(state=State.OK, summary="Operational status: standby, Source: ac line"),
                Result(state=State.OK, summary="Voltage: 12.0 V"),
                Metric("voltage", 12.0),
                Result(state=State.OK, summary="Power: 0.0 W"),
                Metric("power", 0.0),
            ],
            id="standby",
        ),
        pytest.param(
            "201",
            {},
            [
                Result(state=State.OK, summary="Operational status: engaged, Source: ac line"),
                Result(state=State.OK, summary="Voltage: 12.0 V"),
                Metric("voltage", 12.0),
                Result(state=State.OK, summary="Power: 150.0 W"),
                Metric("power", 150.0),
            ],
            id="engaged",
        ),
        pytest.param(
            "208",
            {},
            [
                Result(state=State.OK, summary="Operational status: redundant, Source: ac line"),
                Result(state=State.OK, summary="Voltage: 12.0 V"),
                Metric("voltage", 12.0),
                Result(state=State.OK, summary="Power: 160.0 W"),
                Metric("power", 160.0),
            ],
            id="redundant",
        ),
        pytest.param(
            "203",
            {},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Operational status: not present, Source: ac line",
                ),
                Result(state=State.OK, summary="Voltage: 0.0 V"),
                Metric("voltage", 0.0),
                Result(state=State.OK, summary="Power: 0.0 W"),
                Metric("power", 0.0),
            ],
            id="not_present_stays_checkable",
        ),
        pytest.param(
            "202",
            {"voltage": (11.5, 11.0)},
            [
                Result(state=State.CRIT, summary="Operational status: failed, Source: dc line"),
                Result(state=State.WARN, summary="Voltage: 11.2 V (warn/crit below 11.5 V/11.0 V)"),
                Metric("voltage", 11.2),
                Result(state=State.OK, summary="Power: 140.0 W"),
                Metric("power", 140.0),
            ],
            id="voltage_warn_is_a_lower_bound",
        ),
        pytest.param(
            "205",
            {"voltage": (11.5, 11.0)},
            [
                Result(state=State.WARN, summary="Operational status: warning, Source: invalid"),
                Result(state=State.CRIT, summary="Voltage: 10.0 V (warn/crit below 11.5 V/11.0 V)"),
                Metric("voltage", 10.0),
                Result(state=State.OK, summary="Power: 120.0 W"),
                Metric("power", 120.0),
            ],
            id="voltage_crit_is_a_lower_bound",
        ),
        pytest.param(
            "201",
            {"power": (100.0, 200.0)},
            [
                Result(state=State.OK, summary="Operational status: engaged, Source: ac line"),
                Result(state=State.OK, summary="Voltage: 12.0 V"),
                Metric("voltage", 12.0),
                Result(state=State.WARN, summary="Power: 150.0 W (warn/crit at 100.0 W/200.0 W)"),
                Metric("power", 150.0, levels=(100.0, 200.0)),
            ],
            id="power_levels_are_upper_bounds",
        ),
        pytest.param("999", {}, [], id="unknown_item"),
    ],
)
def test_check_intel_true_scale_psus(
    item: str,
    params: Mapping[str, object],
    expected_results: list[Result | Metric],
) -> None:
    assert (
        list(check_intel_true_scale_psus(item, params, parse_intel_true_scale_psus(STRING_TABLE)))
        == expected_results
    )
