#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.tplink.agent_based.tplink_poe_summary import (
    check_tplink_poe_summary,
    discover_tplink_poe_summary,
    parse_tplink_poe_summary,
)


@pytest.mark.parametrize(
    "string_table, expected_services",
    [
        ([["150"]], [Service()]),
        ([["0"]], []),
        ([], []),
    ],
)
def test_discover_tplink_poe_summary(
    string_table: StringTable, expected_services: Sequence[Service]
) -> None:
    parsed = parse_tplink_poe_summary(string_table)
    assert list(discover_tplink_poe_summary(parsed)) == expected_services


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {},
            [["150"]],
            [
                Result(state=State.OK, summary="15.00 W"),
                Metric("power", 15.0),
            ],
        ),
        (
            {},
            [],
            [],
        ),
        (
            {"levels": (10.0, 20.0)},
            [["150"]],
            [
                Result(
                    state=State.WARN,
                    summary="15.00 W (warn/crit at 10.00 W/20.00 W)",
                ),
                Metric("power", 15.0, levels=(10.0, 20.0)),
            ],
        ),
        (
            {"levels": (10.0, 20.0)},
            [["250"]],
            [
                Result(
                    state=State.CRIT,
                    summary="25.00 W (warn/crit at 10.00 W/20.00 W)",
                ),
                Metric("power", 25.0, levels=(10.0, 20.0)),
            ],
        ),
    ],
)
def test_check_tplink_poe_summary(
    params: Mapping[str, tuple[float, float]],
    string_table: StringTable,
    expected_results: CheckResult,
) -> None:
    parsed = parse_tplink_poe_summary(string_table)
    assert list(check_tplink_poe_summary(params, parsed)) == expected_results
