#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.sophos_memory import (
    check_sophos_memory,
    discover_sophos_memory,
    parse_sophos_memory,
)

LegacyResult = tuple[int, str, Sequence[object]]


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
    assert list(discover_sophos_memory(27)) == [(None, {})]


@pytest.mark.parametrize(
    "string_table, params, expected_result",
    [
        pytest.param(
            [["51"]],
            {},
            [(0, "Usage: 51.00%", [("memory_util", 51, None, None)])],
            id="no_levels_configured",
        ),
        pytest.param(
            [["27"]],
            {"memory_levels": (80, 90)},
            [(0, "Usage: 27.00%", [("memory_util", 27, 80.0, 90.0)])],
            id="ok_below_warn",
        ),
        pytest.param(
            [["85"]],
            {"memory_levels": (80, 90)},
            [
                (
                    1,
                    "Usage: 85.00% (warn/crit at 80.00%/90.00%)",
                    [("memory_util", 85, 80.0, 90.0)],
                )
            ],
            id="warn_above_warn",
        ),
        pytest.param(
            [["95"]],
            {"memory_levels": (80, 90)},
            [
                (
                    2,
                    "Usage: 95.00% (warn/crit at 80.00%/90.00%)",
                    [("memory_util", 95, 80.0, 90.0)],
                )
            ],
            id="crit_above_crit",
        ),
    ],
)
def test_check_sophos_memory(
    string_table: StringTable,
    params: Mapping[str, object],
    expected_result: Sequence[LegacyResult],
) -> None:
    parsed = parse_sophos_memory(string_table)
    assert list(check_sophos_memory(None, params, parsed)) == expected_result
