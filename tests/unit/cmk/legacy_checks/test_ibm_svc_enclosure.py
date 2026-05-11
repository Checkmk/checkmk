#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.ibm_svc_enclosure import (
    check_ibm_svc_enclosure,
    discover_ibm_svc_enclosure,
    parse_ibm_svc_enclosure,
)

STRING_TABLE_13COL: StringTable = [
    [
        "1",
        "online",
        "control",
        "yes",
        "0",
        "io_grp0",
        "2072-24C",
        "7804037",
        "2",
        "1",
        "2",
        "2",
        "24",
    ],
    [
        "2",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804306",
        "2",
        "0",
        "2",
        "2",
        "24",
    ],
    [
        "3",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804326",
        "2",
        "1",
        "2",
        "2",
        "24",
    ],
    [
        "4",
        "online",
        "expansion",
        "yes",
        "0",
        "io_grp0",
        "2072-24E",
        "7804352",
        "2",
        "2",
        "2",
        "2",
        "24",
    ],
]


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            STRING_TABLE_13COL,
            [Service(item="1"), Service(item="2"), Service(item="3"), Service(item="4")],
        ),
    ],
)
def test_discover_ibm_svc_enclosure(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    parsed = parse_ibm_svc_enclosure(string_table)
    result = list(discover_ibm_svc_enclosure(parsed))
    assert sorted(result, key=lambda s: s.item or "") == sorted(
        expected_discoveries, key=lambda s: s.item or ""
    )


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {"levels_lower_online_canisters": (2, 0)},
            STRING_TABLE_13COL,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.WARN, summary="Online canisters: 1 (warn/crit below 2/0) of 2"),
                Result(state=State.OK, summary="Online PSUs: 2 of 2"),
            ],
        ),
        (
            "2",
            {"levels_lower_online_canisters": (-1, -1)},
            STRING_TABLE_13COL,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Online canisters: 0 of 2"),
                Result(state=State.OK, summary="Online PSUs: 2 of 2"),
            ],
        ),
        (
            "3",
            {},
            STRING_TABLE_13COL,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.CRIT, summary="Online canisters: 1 (warn/crit below 2/2) of 2"),
                Result(state=State.OK, summary="Online PSUs: 2 of 2"),
            ],
        ),
        (
            "4",
            {},
            STRING_TABLE_13COL,
            [
                Result(state=State.OK, summary="Status: online"),
                Result(state=State.OK, summary="Online canisters: 2 of 2"),
                Result(state=State.OK, summary="Online PSUs: 2 of 2"),
            ],
        ),
    ],
)
def test_check_ibm_svc_enclosure(
    item: str,
    params: Mapping[str, tuple[int, int] | bool],
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_ibm_svc_enclosure(string_table)
    result = list(check_ibm_svc_enclosure(item, params, parsed))
    assert result == expected_results
