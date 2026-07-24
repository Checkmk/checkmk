#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.meinberg.agent_based.mbg_lantime_ng_fan import (
    check_mbg_lantime_ng_fan,
    discover_mbg_lantime_ng_fan,
    parse_mbg_lantime_ng_fan,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [Service(item="1"), Service(item="2"), Service(item="4"), Service(item="5")],
        ),
    ],
)
def test_discover_mbg_lantime_ng_fan(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for mbg_lantime_ng_fan check."""
    parsed = parse_mbg_lantime_ng_fan(string_table)
    result = list(discover_mbg_lantime_ng_fan(parsed))
    assert result == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "1",
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.OK, summary="Errors: no"),
            ],
        ),
        (
            "2",
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.OK, summary="Errors: no"),
            ],
        ),
        (
            "4",
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.OK, summary="Errors: no"),
            ],
        ),
        (
            "5",
            [["1", "2", "1"], ["2", "2", "1"], ["3", "0", "1"], ["4", "2", "1"], ["5", "2", ""]],
            [
                Result(state=State.OK, summary="Status: on"),
                Result(state=State.UNKNOWN, summary="Errors: not available"),
            ],
        ),
    ],
)
def test_check_mbg_lantime_ng_fan(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    """Test check function for mbg_lantime_ng_fan check."""
    parsed = parse_mbg_lantime_ng_fan(string_table)
    result = list(check_mbg_lantime_ng_fan(item, parsed))
    assert result == expected_results
