#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.quantum_libsmall_door import (
    _Section,
    check_quantum_libsmall_door,
    discovery_quantum_libsmall_door,
    parse_quantum_libsmall_door,
)


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [pytest.param([], None, id="empty"), pytest.param([["1"]], [["1"]], id="non-empty")],
)
def test_parse_quantum_libsmall_door(string_table: StringTable, expected: _Section) -> None:
    assert expected == (parse_quantum_libsmall_door(string_table))


def test_discovery_quantum_libsmall_door():
    assert [Service(item=None, parameters=None)] == list(discovery_quantum_libsmall_door(None))


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param([["1"]], [Result(state=State.CRIT, summary="Library door open")], id="open"),
        pytest.param([["2"]], [Result(state=State.OK, summary="Library door closed")], id="closed"),
        pytest.param(
            [["something"]],
            [Result(state=State.UNKNOWN, summary="Library door unknown")],
            id="unknown",
        ),
        pytest.param(None, [], id="empty"),
    ],
)
def test_check_quantum_libsmall_door(section: _Section, expected: CheckResult) -> None:
    assert expected == list(check_quantum_libsmall_door(section))
