#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.quantum_libsmall_status import (
    _Section,
    check_quantum_libsmall_status,
    discovery_quantum_libsmall_status,
    parse_quantum_libsmall_status,
)


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [("Power", "2")],
            [Service(item=None, parameters=None)],
            id="non-empty",
        ),
    ],
)
def test_discovery_quantum_libsmall_status(section: _Section, expected: DiscoveryResult) -> None:
    assert expected == list(discovery_quantum_libsmall_status(section))


@pytest.mark.parametrize(
    ["string_table", "expected"],
    [
        pytest.param([[]], [], id="empty"),
        pytest.param(
            [[["1.0", "1"]]],
            [("Power", "1")],
            id="single entry",
        ),
        pytest.param(
            [
                [],
                [
                    ["1.0", "1"],
                    ["2.0", "1"],
                    ["3.0", "1"],
                    ["4.0", "1"],
                    ["5.0", "1"],
                    ["6.0", "1"],
                    ["7.0", "1"],
                    ["8.0", "2"],
                ],
            ],
            [
                ("Power", "1"),
                ("Cooling", "1"),
                ("Control", "1"),
                ("Connectivity", "1"),
                ("Robotics", "1"),
                ("Media", "1"),
                ("Drive", "1"),
                ("Operator action request", "2"),
            ],
        ),
        pytest.param(
            [
                [
                    ["1.0", "1"],
                    ["2.0", "1"],
                    ["3.0", "1"],
                    ["4.0", "1"],
                    ["5.0", "1"],
                    ["6.0", "1"],
                    ["7.0", "1"],
                    ["8.0", "2"],
                ],
                [],
            ],
            [
                ("Power", "1"),
                ("Cooling", "1"),
                ("Control", "1"),
                ("Connectivity", "1"),
                ("Robotics", "1"),
                ("Media", "1"),
                ("Drive", "1"),
                ("Operator action request", "2"),
            ],
        ),
    ],
)
def test_parse_quantum_libsmall_status(
    string_table: Sequence[StringTable], expected: _Section
) -> None:
    assert expected == list(parse_quantum_libsmall_status(string_table))


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param([], [], id="empty"),
        pytest.param(
            [("Power", "2")], [Result(state=State.CRIT, summary="Power: failed")], id="RAS failed"
        ),
        pytest.param(
            [("Cooling", "3")],
            [Result(state=State.CRIT, summary="Cooling: degraded")],
            id="RAS degraded",
        ),
        pytest.param(
            [("Connectivity", "4")],
            [Result(state=State.WARN, summary="Connectivity: warning")],
            id="RAS warning",
        ),
        pytest.param(
            [("Robotics", "5")],
            [Result(state=State.OK, summary="Robotics: informational")],
            id="RAS informational",
        ),
        pytest.param(
            [("Media", "6")],
            [Result(state=State.UNKNOWN, summary="Media: unknown")],
            id="RAS unknown",
        ),
        pytest.param(
            [("Drive", "7")],
            [Result(state=State.UNKNOWN, summary="Drive: invalid")],
            id="RAS invalid",
        ),
        pytest.param(
            [("Drive", "status")],
            [Result(state=State.UNKNOWN, summary="Drive: unknown[status]")],
            id="RAS unknown",
        ),
        pytest.param(
            [("Operator action request", "1")],
            [Result(state=State.CRIT, summary="Operator action request: yes")],
            id="OPNEED yes",
        ),
        pytest.param(
            [("Operator action request", "status")],
            [Result(state=State.UNKNOWN, summary="Operator action request: unknown[status]")],
            id="OPNEED unknown",
        ),
        pytest.param(
            [
                ("Power", "1"),
                ("Cooling", "1"),
                ("Control", "1"),
                ("Connectivity", "1"),
                ("Robotics", "1"),
                ("Media", "1"),
                ("Drive", "1"),
                ("Operator action request", "2"),
            ],
            [
                Result(state=State.OK, summary="Power: good"),
                Result(state=State.OK, summary="Cooling: good"),
                Result(state=State.OK, summary="Control: good"),
                Result(state=State.OK, summary="Connectivity: good"),
                Result(state=State.OK, summary="Robotics: good"),
                Result(state=State.OK, summary="Media: good"),
                Result(state=State.OK, summary="Drive: good"),
                Result(state=State.OK, summary="Operator action request: no"),
            ],
            id="everything ok",
        ),
    ],
)
def test_check_quantum_libsmall_status(section: _Section, expected: CheckResult) -> None:
    assert expected == list(check_quantum_libsmall_status(section))
