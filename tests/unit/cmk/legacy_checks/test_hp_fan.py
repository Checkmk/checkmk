#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.hp_fan import check_hp_fan, discover_hp_fan, parse_hp_fan


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]],
            [Service(item="2/0"), Service(item="3/1"), Service(item="4/2")],
        ),
    ],
)
def test_discover_hp_fan(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_hp_fan(string_table)
    assert sorted(discover_hp_fan(parsed)) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, string_table, expected_result",
    [
        (
            "2/0",
            [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]],
            Result(state=State.OK, summary="ok"),
        ),
        (
            "3/1",
            [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]],
            Result(state=State.WARN, summary="underspeed"),
        ),
        (
            "4/2",
            [["0", "2", "5"], ["1", "3", "3"], ["2", "4", "1"]],
            Result(state=State.CRIT, summary="removed"),
        ),
    ],
)
def test_check_hp_fan(item: str, string_table: StringTable, expected_result: Result) -> None:
    parsed = parse_hp_fan(string_table)
    assert list(check_hp_fan(item, parsed)) == [expected_result]
