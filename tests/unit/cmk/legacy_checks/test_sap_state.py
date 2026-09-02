#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks import sap_state

_STRING_TABLE: StringTable = [
    ["SID1", "OK"],
    ["SID2", "CRIT"],
    ["extra", "line", "ignored"],
]


def test_discover_sap_state() -> None:
    assert list(sap_state.discover_sap_state(_STRING_TABLE)) == [
        Service(item="SID1"),
        Service(item="SID2"),
    ]


@pytest.mark.parametrize(
    "item, expected",
    [
        ("SID1", [Result(state=State.OK, summary="Status: OK")]),
        ("SID2", [Result(state=State.CRIT, summary="Status: CRIT")]),
        ("MISSING", []),
    ],
)
def test_check_sap_state(item: str, expected: list[Result]) -> None:
    assert list(sap_state.check_sap_state(item, _STRING_TABLE)) == expected
