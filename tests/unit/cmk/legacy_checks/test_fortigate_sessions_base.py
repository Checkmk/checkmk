#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.fortigate_sessions_base import (
    check_fortigate_sessions_base,
    discover_fortigate_sessions_base,
    parse_fortigate_sessions_base,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["1000"]], 1000),
        ([], None),
        ([["not a number"]], None),
    ],
)
def test_parse_fortigate_sessions_base(string_table: StringTable, expected: int | None) -> None:
    assert parse_fortigate_sessions_base(string_table) == expected


def test_discover_fortigate_sessions_base() -> None:
    assert list(discover_fortigate_sessions_base(1000)) == [Service()]


def test_check_fortigate_sessions_base() -> None:
    assert list(check_fortigate_sessions_base({"levels": (100000, 150000)}, 1000)) == [
        Result(state=State.OK, summary="Sessions: 1000"),
        Metric("session", 1000.0, levels=(100000.0, 150000.0)),
    ]
