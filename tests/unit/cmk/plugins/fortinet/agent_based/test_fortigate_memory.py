#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.fortinet.agent_based.fortigate_memory import (
    check_fortigate_memory,
    discover_fortigate_memory,
    parse_fortigate_memory,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["42"]], 42),
        ([], None),
        ([["not a number"]], None),
    ],
)
def test_parse_fortigate_memory(string_table: StringTable, expected: int | None) -> None:
    assert parse_fortigate_memory(string_table) == expected


def test_discover_fortigate_memory() -> None:
    assert list(discover_fortigate_memory(42)) == [Service()]


@pytest.mark.parametrize(
    "params, section, expected_results",
    [
        (
            {"levels": (30.0, 80.0)},
            42,
            [
                Result(state=State.WARN, summary="Usage: 42.00% (warn/crit at 30.00%/80.00%)"),
                Metric("mem_usage", 42.0, levels=(30.0, 80.0)),
            ],
        ),
        (
            {"levels": (-80.0, -30.0)},
            42,
            [
                Result(state=State.WARN, summary="Usage: 42.00% (warn/crit at 20.00%/70.00%)"),
                Metric("mem_usage", 42.0, levels=(20.0, 70.0)),
            ],
        ),
        (
            {"levels": (-80, -30)},
            42,
            [
                Result(state=State.UNKNOWN, summary="Absolute levels are not supported"),
                Result(state=State.OK, summary="Usage: 42.00%"),
                Metric("mem_usage", 42.0),
            ],
        ),
    ],
)
def test_check_fortigate_memory(
    params: Mapping[str, object],
    section: int,
    expected_results: Sequence[object],
) -> None:
    assert list(check_fortigate_memory(params, section)) == expected_results
