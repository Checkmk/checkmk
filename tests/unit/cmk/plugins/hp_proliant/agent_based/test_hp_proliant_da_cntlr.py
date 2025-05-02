#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.hp_proliant.agent_based.hp_proliant_da_cntlr import (
    check_hp_proliant_da_cntlr,
    ControllerID,
    discovery_hp_proliant_da_cntlr,
    parse_hp_proliant_da_cntlr,
)

STRING_TABLE = [
    ["0", "54", "0", "2", "1", "2", "2", "N/A"],
    ["3", "52", "3", "3", "1", "2", "2", "PXXXX0BRH6X59X"],
    ["6", "1", "6", "2", "1", "8", "1", "PEYHN0ARCC307J"],
    ["9", "0", "0", "0", "0", "0", "0", ""],
]


def test_discovery() -> None:
    assert list(
        discovery_hp_proliant_da_cntlr(section=parse_hp_proliant_da_cntlr(STRING_TABLE))
    ) == [
        Service(item="0"),
        Service(item="3"),
        Service(item="6"),
        Service(item="9"),
    ]


@pytest.mark.parametrize(
    ["item", "expected"],
    [
        pytest.param(
            "0",
            [
                Result(
                    state=State.OK,
                    summary="Condition: ok, Board-Condition: ok, Board-Status: ok (Role: other, Model: 54, Slot: 0, Serial: N/A)",
                )
            ],
        ),
        pytest.param(
            "3",
            [
                Result(
                    state=State.WARN,
                    summary="Condition: degraded, Board-Condition: ok, Board-Status: ok (Role: other, Model: 52, Slot: 3, Serial: PXXXX0BRH6X59X)",
                )
            ],
        ),
        pytest.param(
            "6",
            [
                Result(
                    state=State.WARN,
                    summary="Condition: ok, Board-Condition: other, Board-Status: enabled (Role: other, Model: 1, Slot: 6, Serial: PEYHN0ARCC307J)",
                    details="The instrument agent does not recognize the status of the controller. You may need to upgrade the instrument agent.",
                )
            ],
        ),
        pytest.param(
            "9", [Result(state=State.UNKNOWN, summary="Controller not found in SNMP data")]
        ),
        pytest.param(
            "foo", [Result(state=State.UNKNOWN, summary="Controller not found in SNMP data")]
        ),
    ],
)
def test_check(item: ControllerID, expected: list[Result]) -> None:
    assert (
        list(
            check_hp_proliant_da_cntlr(item=item, section=parse_hp_proliant_da_cntlr(STRING_TABLE))
        )
        == expected
    )
