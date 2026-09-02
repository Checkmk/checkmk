#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.sophos.agent_based.sophos_memory import (
    check_sophos_memory,
    discover_sophos_memory,
    Params,
    parse_sophos_memory,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        pytest.param([["27"]], 27, id="single_value"),
        pytest.param([["bogus"]], None, id="not_a_number"),
        pytest.param([], None, id="empty"),
        pytest.param([[]], None, id="empty_row"),
    ],
)
def test_parse_sophos_memory(string_table: StringTable, expected: int | None) -> None:
    assert parse_sophos_memory(string_table) == expected


def test_discover_sophos_memory_yields_single_service() -> None:
    assert list(discover_sophos_memory(27)) == [Service()]


@pytest.mark.parametrize(
    "string_table, params, expected_result",
    [
        pytest.param(
            [["51"]],
            {},
            [
                Result(state=State.OK, summary="Usage: 51.00%"),
                Metric("memory_util", 51.0),
            ],
            id="no_levels_configured",
        ),
        pytest.param(
            [["27"]],
            {"memory_levels": (80, 90)},
            [
                Result(state=State.OK, summary="Usage: 27.00%"),
                Metric("memory_util", 27.0, levels=(80.0, 90.0)),
            ],
            id="ok_below_warn",
        ),
        pytest.param(
            [["85"]],
            {"memory_levels": (80, 90)},
            [
                Result(state=State.WARN, summary="Usage: 85.00% (warn/crit at 80.00%/90.00%)"),
                Metric("memory_util", 85.0, levels=(80.0, 90.0)),
            ],
            id="warn_above_warn",
        ),
        pytest.param(
            [["95"]],
            {"memory_levels": (80, 90)},
            [
                Result(state=State.CRIT, summary="Usage: 95.00% (warn/crit at 80.00%/90.00%)"),
                Metric("memory_util", 95.0, levels=(80.0, 90.0)),
            ],
            id="crit_above_crit",
        ),
    ],
)
def test_check_sophos_memory(
    string_table: StringTable,
    params: Params,
    expected_result: Sequence[Result | Metric],
) -> None:
    parsed = parse_sophos_memory(string_table)
    assert parsed is not None
    assert list(check_sophos_memory(params, parsed)) == expected_result
