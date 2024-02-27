#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.quantum_libsmall_status import (
    check_quantum_libsmall_status,
    inventory_quantum_libsmall_status,
    parse_quantum_libsmall_status,
)


@pytest.mark.parametrize(
    ["parsed", "expected"],
    [
        pytest.param([], [], id="empty"),
        pytest.param([("Power", "2")], [(None, None)], id="non-empty"),
    ],
)
def test_inventory_quantum_libsmall_status(parsed: list[tuple[str, str]], expected: list) -> None:
    assert expected == list(inventory_quantum_libsmall_status(parsed))


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
    string_table: list[list[list[str]]], expected: list[tuple[str, str]]
) -> None:
    assert expected == list(parse_quantum_libsmall_status(string_table))


@pytest.mark.parametrize(
    ["parsed", "expected"],
    [
        pytest.param([], [], id="empty"),
        pytest.param([("Power", "2")], [(2, "Power: failed")], id="RAS failed"),
        pytest.param([("Cooling", "3")], [(2, "Cooling: degraded")], id="RAS degraded"),
        pytest.param([("Connectivity", "4")], [(1, "Connectivity: warning")], id="RAS warning"),
        pytest.param([("Robotics", "5")], [(0, "Robotics: informational")], id="RAS informational"),
        pytest.param([("Media", "6")], [(3, "Media: unknown")], id="RAS unknown"),
        pytest.param([("Drive", "7")], [(3, "Drive: invalid")], id="RAS invalid"),
        pytest.param([("Drive", "status")], [(3, "Drive: unknown[status]")], id="RAS unknown"),
        pytest.param(
            [("Operator action request", "1")],
            [(2, "Operator action request: yes")],
            id="OPNEED yes",
        ),
        pytest.param(
            [("Operator action request", "status")],
            [(3, "Operator action request: unknown[status]")],
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
                (0, "Power: good"),
                (0, "Cooling: good"),
                (0, "Control: good"),
                (0, "Connectivity: good"),
                (0, "Robotics: good"),
                (0, "Media: good"),
                (0, "Drive: good"),
                (0, "Operator action request: no"),
            ],
            id="everything ok",
        ),
    ],
)
def test_check_quantum_libsmall_status(
    parsed: list[tuple[str, str]], expected: list[tuple[int, str]]
) -> None:
    assert expected == list(check_quantum_libsmall_status(None, {}, parsed))
