#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.hp.agent_based.hp_psu import check_hp_psu, discover_hp_psu, parse_hp_psu


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [["1", "3", "25"], ["2", "3", "23"]],
            [Service(item="1"), Service(item="2")],
        ),
    ],
)
def test_discover_hp_psu(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_hp_psu(string_table)
    assert sorted(discover_hp_psu(parsed), key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        (
            "1",
            [["1", "3", "25"], ["2", "3", "23"]],
            [Result(state=State.OK, summary="Powered")],
        ),
        (
            "2",
            [["1", "3", "25"], ["2", "3", "23"]],
            [Result(state=State.OK, summary="Powered")],
        ),
    ],
)
def test_check_hp_psu(
    item: str, string_table: StringTable, expected_results: Sequence[Result]
) -> None:
    parsed = parse_hp_psu(string_table)
    assert list(check_hp_psu(item, parsed)) == expected_results
