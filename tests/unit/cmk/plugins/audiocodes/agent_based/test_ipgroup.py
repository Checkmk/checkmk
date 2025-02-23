#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Metric, Result, Service, State, StringTable
from cmk.plugins.audiocodes.agent_based.ipgroup import (
    check_audiocodes_ipgroup,
    discover_audiocodes_ipgroup,
    IPGroup,
    parse_audiocodes_ipgroup,
)

_STRING_TABLE = [
    [
        ["0", "1", "0", "", "N11 intern", "Connected"],
        ["5", "1", "0", "", "N13 extern", "NA"],
        ["7", "2", "2", "", "CSIP HAN", "Disconnected"],
    ],
    [["0", "12", "13"]],
]

_STRING_TABLE_WITHOUT_CALL_INFORMATION = [
    [
        ["0", "1", "0", "", "N11 intern", "Connected"],
        ["5", "1", "0", "", "N13 extern", "NA"],
        ["7", "2", "2", "", "CSIP HAN", "Disconnected"],
    ],
    [],
]


def _parsed_section(string_table: Sequence[StringTable]) -> Mapping[str, IPGroup]:
    section = parse_audiocodes_ipgroup(string_table)
    assert section
    return section


def test_discovery_function() -> None:
    assert list(discover_audiocodes_ipgroup(_parsed_section(_STRING_TABLE))) == [
        Service(item="0 N11 intern"),
        Service(item="5 N13 extern"),
        Service(item="7 CSIP HAN"),
    ]


@pytest.mark.parametrize(
    "item, string_table, expected",
    [
        pytest.param(
            "0 N11 intern",
            _STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active",
                    details="IP group name: N11 intern, Type: Server, IP group index: 0, Description: None, Proxy set connectivity: Connected",
                ),
                Result(state=State.OK, summary="Active calls in: 12"),
                Metric("audiocodes_ipgroup_active_calls_in", 12.0),
                Result(state=State.OK, summary="Active calls out: 13"),
                Metric("audiocodes_ipgroup_active_calls_out", 13.0),
            ],
            id="Everything OK. Active calls in and out available",
        ),
        pytest.param(
            "5 N13 extern",
            _STRING_TABLE,
            [
                Result(
                    state=State.OK,
                    summary="Status: active",
                    details="IP group name: N13 extern, Type: Server, IP group index: 5, Description: None, Proxy set connectivity: NA",
                ),
            ],
            id="Connect status is not available, but overall state is OK",
        ),
        pytest.param(
            "7 CSIP HAN",
            _STRING_TABLE,
            [
                Result(
                    state=State.CRIT,
                    summary="Status: notInService",
                    details="IP group name: CSIP HAN, Type: Gateway, IP group index: 7, Description: None, Proxy set connectivity: Disconnected",
                ),
            ],
            id="Bad status. Overall state is CRIT",
        ),
        pytest.param(
            "0 N11 intern",
            _STRING_TABLE_WITHOUT_CALL_INFORMATION,
            [
                Result(
                    state=State.OK,
                    summary="Status: active",
                    details="IP group name: N11 intern, Type: Server, IP group index: 0, Description: None, Proxy set connectivity: Connected",
                ),
            ],
            id="OK. No call information available",
        ),
    ],
)
def test_check_function(
    item: str,
    string_table: Sequence[StringTable],
    expected: CheckResult,
) -> None:
    assert list(check_audiocodes_ipgroup(item, _parsed_section(string_table))) == expected
