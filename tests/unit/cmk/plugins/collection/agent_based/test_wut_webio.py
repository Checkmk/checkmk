#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.wut_webio import (
    AS_DISCOVERED,
    check_wut_webio,
    DEFAULT_STATE_EVALUATION,
    discover_wut_webio,
    parse_wut_webio,
    Section,
    STATE_EVAL_KEY,
    STATES_DURING_DISC_KEY,
)

STRING_TABLE: Sequence[StringTable] = [
    [],
    [
        ["WEBIO-094849", "", "", ""],
        ["", "1", "Input 0", "1"],
        ["", "2", "Input 1", "0"],
        ["", "2", "Input 2", ""],
    ],
    [],
]

ITEM = "WEBIO-094849 Input 0"


def _parse_mandatory(string_table: Sequence[StringTable]) -> Section:
    section = parse_wut_webio(string_table)
    assert section
    return section


def test_discovery() -> None:
    assert list(discover_wut_webio(_parse_mandatory(STRING_TABLE))) == [
        Service(item=ITEM, parameters={"states_during_discovery": "On"}),
        Service(item="WEBIO-094849 Input 1", parameters={"states_during_discovery": "Off"}),
        Service(item="WEBIO-094849 Input 2", parameters={"states_during_discovery": "Unknown"}),
    ]


@pytest.mark.parametrize(
    "params, expected",
    [
        (
            {STATE_EVAL_KEY: DEFAULT_STATE_EVALUATION, STATES_DURING_DISC_KEY: "Off"},
            [Result(state=State.OK, summary="Input (Index: 1) is in state: On")],
        ),
        (
            {STATE_EVAL_KEY: AS_DISCOVERED, STATES_DURING_DISC_KEY: "Off"},
            [Result(state=State.CRIT, summary="Input (Index: 1) is in state: On")],
        ),
    ],
)
def test_check(params: Mapping[str, object], expected: CheckResult) -> None:
    assert list(check_wut_webio(ITEM, params, _parse_mandatory(STRING_TABLE))) == expected


def test_check_unknown() -> None:
    assert list(
        check_wut_webio(
            "WEBIO-094849 Input 2",
            params={STATE_EVAL_KEY: DEFAULT_STATE_EVALUATION, STATES_DURING_DISC_KEY: "Unknown"},
            section=_parse_mandatory(STRING_TABLE),
        )
    ) == [Result(state=State.UNKNOWN, summary="Input (Index: 2) is in state: Unknown")]
