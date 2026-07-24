#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.netscaler_mem import (
    check_netscaler_mem,
    discover_netscaler_mem,
    parse_netscaler_mem,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["4.2", "23"]], [Service()]),
    ],
)
def test_discover_netscaler_mem(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for netscaler_mem check."""
    parsed = parse_netscaler_mem(string_table)
    result = list(discover_netscaler_mem(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "params, string_table, expected_results",
    [
        (
            {"levels": (80.0, 90.0)},
            [["4.2", "23"]],
            [
                Result(state=State.OK, summary="Usage: 4.20% - 989 KiB of 23.0 MiB"),
                Metric(
                    "mem_used",
                    1012924.4160000001,
                    levels=(19293798.400000002, 21705523.2),
                    boundaries=(0, 24117248.0),
                ),
            ],
        ),
    ],
)
def test_check_netscaler_mem(
    params: Mapping[str, tuple[float, float]],
    string_table: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for netscaler_mem check."""
    parsed = parse_netscaler_mem(string_table)
    result = list(check_netscaler_mem(params, parsed))
    assert result == expected_results
