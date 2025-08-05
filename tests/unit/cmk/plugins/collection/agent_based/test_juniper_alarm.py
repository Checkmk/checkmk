#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.juniper_alarm import (
    CHECK_DEFAULT_PARAMS,
    check_juniper_alarm,
    discover_juniper_alarm,
    parse_juniper_alarm,
)

STRING_TABLE_UNKNOWN = [["7"], ["2"], ["2"]]
STRING_TABLE_OK = [["2"], ["2"], ["2"]]
STRING_TABLE_CRIT = [["4"], ["2"], ["2"]]


def test_discover_juniper_alarm() -> None:
    section = parse_juniper_alarm(STRING_TABLE_UNKNOWN)
    assert section is not None
    assert list(discover_juniper_alarm(section)) == [Service()]


@pytest.mark.parametrize(
    "string_table, params, expected",
    [
        pytest.param(
            STRING_TABLE_CRIT,
            CHECK_DEFAULT_PARAMS,
            [Result(state=State.CRIT, summary="Status: alert, failed, not working (major)")],
            id="Critical status",
        ),
        pytest.param(
            STRING_TABLE_OK,
            CHECK_DEFAULT_PARAMS,
            [
                Result(state=State.OK, summary="Status: OK, good, normally working"),
            ],
            id="OK status",
        ),
        pytest.param(
            STRING_TABLE_OK,
            {"state_2": 1},
            [
                Result(state=State.WARN, summary="Status: OK, good, normally working"),
            ],
            id="WARN status because of params",
        ),
        pytest.param(
            STRING_TABLE_CRIT,
            CHECK_DEFAULT_PARAMS,
            [Result(state=State.CRIT, summary="Status: alert, failed, not working (major)")],
            id="Critical status",
        ),
    ],
)
def test_check_juniper_alarm(
    string_table: StringTable,
    params: Mapping[str, int],
    expected: CheckResult,
) -> None:
    section = parse_juniper_alarm(string_table)
    assert section is not None
    assert list(check_juniper_alarm(params, section)) == list(expected)
