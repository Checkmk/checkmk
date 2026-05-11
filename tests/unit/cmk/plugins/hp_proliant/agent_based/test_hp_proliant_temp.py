#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.hp_proliant.agent_based.hp_proliant_temp import (
    check_hp_proliant_temp,
    discover_hp_proliant_temp,
    parse_hp_proliant_temp,
)

_STRING_TABLE = [
    ["1", "11", "27", "45", "2"],
    ["2", "6", "40", "70", "2"],
    ["3", "6", "40", "70", "2"],
    ["4", "7", "33", "87", "2"],
    ["5", "7", "34", "87", "2"],
    ["6", "7", "36", "80", "2"],
    ["7", "7", "36", "80", "2"],
    ["8", "7", "36", "80", "2"],
    ["9", "7", "36", "80", "2"],
    ["10", "7", "36", "80", "2"],
    ["11", "7", "36", "80", "2"],
    ["12", "3", "35", "60", "2"],
    ["13", "3", "50", "105", "2"],
    ["14", "3", "41", "95", "2"],
    ["15", "10", "35", "0", "2"],
    ["16", "10", "34", "0", "2"],
    ["17", "10", "36", "80", "2"],
    ["18", "10", "36", "80", "2"],
    ["19", "3", "35", "115", "2"],
    ["20", "3", "35", "115", "2"],
    ["21", "3", "35", "115", "2"],
    ["22", "3", "35", "115", "2"],
    ["23", "3", "30", "65", "2"],
    ["26", "3", "42", "100", "2"],
    ["27", "3", "40", "100", "2"],
    ["28", "3", "37", "90", "2"],
    ["31", "5", "85", "100", "2"],
    ["35", "5", "35", "67", "2"],
    ["36", "5", "37", "67", "2"],
    ["37", "5", "37", "67", "2"],
    ["38", "5", "36", "67", "2"],
    ["41", "3", "39", "90", "2"],
    ["42", "3", "38", "90", "2"],
    ["43", "3", "40", "90", "2"],
    ["46", "8", "36", "65", "2"],
    ["47", "8", "36", "65", "2"],
    ["48", "12", "40", "90", "2"],
    ["49", "12", "38", "90", "2"],
    ["50", "3", "32", "60", "2"],
    ["51", "3", "0", "60", "1"],
]


def test_discover_hp_proliant_temp() -> None:
    parsed = parse_hp_proliant_temp(_STRING_TABLE)
    assert sorted(discover_hp_proliant_temp(parsed), key=lambda s: s.item or "") == sorted(
        [
            Service(item="1 (ambient)"),
            Service(item="2 (cpu)"),
            Service(item="3 (cpu)"),
            Service(item="4 (memory)"),
            Service(item="5 (memory)"),
            Service(item="6 (memory)"),
            Service(item="7 (memory)"),
            Service(item="8 (memory)"),
            Service(item="9 (memory)"),
            Service(item="10 (memory)"),
            Service(item="11 (memory)"),
            Service(item="12 (system)"),
            Service(item="13 (system)"),
            Service(item="14 (system)"),
            Service(item="15 (powerSupply)"),
            Service(item="16 (powerSupply)"),
            Service(item="17 (powerSupply)"),
            Service(item="18 (powerSupply)"),
            Service(item="19 (system)"),
            Service(item="20 (system)"),
            Service(item="21 (system)"),
            Service(item="22 (system)"),
            Service(item="23 (system)"),
            Service(item="26 (system)"),
            Service(item="27 (system)"),
            Service(item="28 (system)"),
            Service(item="31 (ioBoard)"),
            Service(item="35 (ioBoard)"),
            Service(item="36 (ioBoard)"),
            Service(item="37 (ioBoard)"),
            Service(item="38 (ioBoard)"),
            Service(item="41 (system)"),
            Service(item="42 (system)"),
            Service(item="43 (system)"),
            Service(item="46 (storage)"),
            Service(item="47 (storage)"),
            Service(item="48 (chassis)"),
            Service(item="49 (chassis)"),
            Service(item="50 (system)"),
        ],
        key=lambda s: s.item or "",
    )


def _expected(temp: float, threshold: float | None) -> list[Result | Metric]:
    if threshold is not None:
        return [
            Metric("temp", temp, levels=(threshold, threshold)),
            Result(state=State.OK, summary=f"Temperature: {temp:.1f} °C"),
            Result(state=State.OK, notice="State on device: Unit: ok"),
            Result(
                state=State.OK,
                notice="Configuration: prefer user levels over device levels (used device levels)",
            ),
        ]
    # Without device levels the temperature lib falls back to the user track,
    # which drops the device status notice.
    return [
        Metric("temp", temp),
        Result(state=State.OK, summary=f"Temperature: {temp:.1f} °C"),
        Result(
            state=State.OK,
            notice="Configuration: prefer user levels over device levels (no levels found)",
        ),
    ]


@pytest.mark.parametrize(
    "item, expected_results",
    [
        ("1 (ambient)", _expected(27.0, 45.0)),
        ("10 (memory)", _expected(36.0, 80.0)),
        ("11 (memory)", _expected(36.0, 80.0)),
        ("12 (system)", _expected(35.0, 60.0)),
        ("13 (system)", _expected(50.0, 105.0)),
        ("14 (system)", _expected(41.0, 95.0)),
        ("15 (powerSupply)", _expected(35.0, None)),
        ("16 (powerSupply)", _expected(34.0, None)),
        ("17 (powerSupply)", _expected(36.0, 80.0)),
        ("18 (powerSupply)", _expected(36.0, 80.0)),
        ("19 (system)", _expected(35.0, 115.0)),
        ("2 (cpu)", _expected(40.0, 70.0)),
        ("20 (system)", _expected(35.0, 115.0)),
        ("21 (system)", _expected(35.0, 115.0)),
        ("22 (system)", _expected(35.0, 115.0)),
        ("23 (system)", _expected(30.0, 65.0)),
        ("26 (system)", _expected(42.0, 100.0)),
        ("27 (system)", _expected(40.0, 100.0)),
        ("28 (system)", _expected(37.0, 90.0)),
        ("3 (cpu)", _expected(40.0, 70.0)),
        ("31 (ioBoard)", _expected(85.0, 100.0)),
        ("35 (ioBoard)", _expected(35.0, 67.0)),
        ("36 (ioBoard)", _expected(37.0, 67.0)),
        ("37 (ioBoard)", _expected(37.0, 67.0)),
        ("38 (ioBoard)", _expected(36.0, 67.0)),
        ("4 (memory)", _expected(33.0, 87.0)),
        ("41 (system)", _expected(39.0, 90.0)),
        ("42 (system)", _expected(38.0, 90.0)),
        ("43 (system)", _expected(40.0, 90.0)),
        ("46 (storage)", _expected(36.0, 65.0)),
        ("47 (storage)", _expected(36.0, 65.0)),
        ("48 (chassis)", _expected(40.0, 90.0)),
        ("49 (chassis)", _expected(38.0, 90.0)),
        ("5 (memory)", _expected(34.0, 87.0)),
        ("50 (system)", _expected(32.0, 60.0)),
        ("6 (memory)", _expected(36.0, 80.0)),
        ("7 (memory)", _expected(36.0, 80.0)),
        ("8 (memory)", _expected(36.0, 80.0)),
        ("9 (memory)", _expected(36.0, 80.0)),
    ],
)
def test_check_hp_proliant_temp(item: str, expected_results: Sequence[Result | Metric]) -> None:
    parsed = parse_hp_proliant_temp(_STRING_TABLE)
    assert list(check_hp_proliant_temp(item, {}, parsed)) == expected_results
