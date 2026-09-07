#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.steelhead_connections import (
    check_steelhead_connections,
    discover_steelhead_connections,
    parse_steelhead_connections,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["1.0", "1619"],
                ["2.0", "1390"],
                ["3.0", "0"],
                ["4.0", "4"],
                ["5.0", "1615"],
                ["6.0", "347"],
                ["7.0", "3009"],
            ],
            [Service()],
        ),
    ],
)
def test_discover_steelhead_connections(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    section = parse_steelhead_connections(string_table)
    result = list(discover_steelhead_connections(section))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {},
            [
                ["1.0", "1619"],
                ["2.0", "1390"],
                ["3.0", "0"],
                ["4.0", "4"],
                ["5.0", "1615"],
                ["6.0", "347"],
                ["7.0", "3009"],
            ],
            [
                Result(state=State.OK, summary="Total connections: 3009"),
                Result(state=State.OK, summary="Passthrough: 1390"),
                Metric("passthrough", 1390),
                Result(state=State.OK, summary="Optimized: 1619"),
                Result(state=State.OK, summary="Active: 347"),
                Metric("active", 347),
                Result(state=State.OK, summary="Established: 1615"),
                Metric("established", 1615),
                Result(state=State.OK, summary="Half opened: 0"),
                Metric("halfOpened", 0),
                Result(state=State.OK, summary="Half closed: 4"),
                Metric("halfClosed", 4),
            ],
        ),
    ],
)
def test_check_steelhead_connections(
    params: Mapping[str, tuple[int, int]],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    section = parse_steelhead_connections(string_table)
    result = list(check_steelhead_connections(params, section))
    assert result == expected_results
