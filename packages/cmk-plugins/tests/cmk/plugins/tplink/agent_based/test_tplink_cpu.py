#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.tplink.agent_based.tplink_cpu import (
    check_tplink_cpu_,
    discover_tplink_cpu,
    parse_tplink_cpu,
)


@pytest.mark.parametrize(
    "string_table, expected_services",
    [
        ([["21"]], [Service()]),
        ([["21"], ["22"]], [Service()]),
        ([], []),
    ],
)
def test_discover_tplink_cpu(
    string_table: StringTable, expected_services: Sequence[Service]
) -> None:
    parsed = parse_tplink_cpu(string_table)
    assert list(discover_tplink_cpu(parsed)) == expected_services


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {},
            [["21"]],
            [
                Result(state=State.OK, summary="Total CPU: 21.00%"),
                Metric("util", 21.0, boundaries=(0, None)),
            ],
        ),
        (
            {},
            [["20"], ["40"]],
            [
                Result(state=State.OK, summary="Total CPU: 30.00%"),
                Metric("util", 30.0, boundaries=(0, None)),
            ],
        ),
        (
            {},
            [],
            [],
        ),
        (
            {"util": (80.0, 90.0)},
            [["85"]],
            [
                Result(
                    state=State.WARN,
                    summary="Total CPU: 85.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("util", 85.0, levels=(80.0, 90.0), boundaries=(0, None)),
            ],
        ),
        (
            {"util": (80.0, 90.0)},
            [["95"]],
            [
                Result(
                    state=State.CRIT,
                    summary="Total CPU: 95.00% (warn/crit at 80.00%/90.00%)",
                ),
                Metric("util", 95.0, levels=(80.0, 90.0), boundaries=(0, None)),
            ],
        ),
    ],
)
def test_check_tplink_cpu(  # type: ignore[misc]
    params: Mapping[str, Any],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    parsed = parse_tplink_cpu(string_table)
    assert list(check_tplink_cpu_(params, parsed, {})) == expected_results
