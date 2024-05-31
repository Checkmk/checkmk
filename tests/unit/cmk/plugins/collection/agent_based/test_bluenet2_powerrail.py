#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.bluenet2_powerrail import (
    check_bluenet2_powerrail_phases,
    discover_bluenet2_powerrail_phases,
    parse_bluenet2_powerrail,
)

# NOTE: In here only the discovery and check function for the phases are tested
# but all of the other ones work in the same manner

_STRING_TABLE = [
    [["1.1", "\x00\x00\x00ÿÿÿ\x00\x00", "Inlet 1", "Inlet 1"]],
    [
        ["1.1.1", "\x00\x00\x00\x00ÿÿ\x00\x00", "Phase 1", "Phase 1"],
        ["1.1.2", "\x00\x00\x00\x01ÿÿ\x00\x00", "Phase 2", "Phase 2"],
        ["1.1.3", "\x00\x00\x00\x02ÿÿ\x00\x00", "Phase 3", "Phase 3"],
    ],
    [
        ["1.1.1.0.0.1", "\x00\x04\x00\x00ÿÿ\x00\x00", "RCM Phase 1", "RCM Phase 1"],
        ["1.1.2.0.0.2", "\x00\x04\x00\x01ÿÿ\x00\x00", "RCM Phase 2", "RCM Phase 2"],
        ["1.1.3.0.0.3", "\x00\x04\x00\x02ÿÿ\x00\x00", "RCM Phase 3", "RCM Phase 3"],
    ],
    [
        ["0.0.0.0.255.255.0.1", "1", "2", "-2", "23424"],
        ["0.0.0.0.255.255.0.4", "4", "2", "-2", "99"],
        ["0.0.0.0.255.255.0.5", "5", "2", "-2", "261"],
        ["0.0.0.0.255.255.0.17", "17", "2", "-3", "-791"],
        ["0.0.0.0.255.255.0.18", "18", "2", "-1", "2309"],
        ["0.0.0.0.255.255.0.19", "19", "2", "-1", "1826"],
        ["0.0.0.0.255.255.0.20", "20", "2", "-1", "4707"],
        ["0.0.0.0.255.255.0.22", "22", "2", "-1", "-1413"],
        ["0.0.0.0.255.255.0.23", "23", "2", "-2", "4999"],
        ["0.0.0.0.255.255.0.32", "32", "2", "-4", "2523774"],
        ["0.0.0.0.255.255.0.34", "34", "2", "-4", "1378451"],
        ["0.0.0.0.255.255.0.36", "36", "2", "-4", "2027360"],
        ["0.0.0.0.255.255.0.38", "38", "2", "-4", "2027360"],
        ["0.0.0.1.255.255.0.1", "1", "2", "-2", "23410"],
        ["0.0.0.1.255.255.0.4", "4", "2", "-2", "95"],
        ["0.0.0.1.255.255.0.5", "5", "2", "-2", "351"],
        ["0.0.0.1.255.255.0.17", "17", "2", "-3", "-717"],
        ["0.0.0.1.255.255.0.18", "18", "2", "-1", "2234"],
        ["0.0.0.1.255.255.0.19", "19", "2", "-1", "1602"],
        ["0.0.0.1.255.255.0.20", "20", "2", "-1", "5180"],
        ["0.0.0.1.255.255.0.22", "22", "2", "-1", "-1571"],
        ["0.0.0.1.255.255.0.23", "23", "2", "-2", "4997"],
        ["0.0.0.1.255.255.0.32", "32", "2", "-4", "2407491"],
        ["0.0.0.1.255.255.0.34", "34", "2", "-4", "1302485"],
        ["0.0.0.1.255.255.0.36", "36", "2", "-4", "1842643"],
        ["0.0.0.1.255.255.0.38", "38", "2", "-4", "1842643"],
        ["0.0.0.2.255.255.0.1", "1", "2", "-2", "23480"],
        ["0.0.0.2.255.255.0.4", "4", "2", "-2", "67"],
        ["0.0.0.2.255.255.0.5", "5", "2", "-2", "140"],
        ["0.0.0.2.255.255.0.17", "17", "2", "-3", "-684"],
        ["0.0.0.2.255.255.0.18", "18", "2", "-1", "1563"],
        ["0.0.0.2.255.255.0.19", "19", "2", "-1", "1069"],
        ["0.0.0.2.255.255.0.20", "20", "2", "-1", "2418"],
        ["0.0.0.2.255.255.0.22", "22", "2", "-1", "-1141"],
        ["0.0.0.2.255.255.0.23", "23", "2", "-2", "4998"],
        ["0.0.0.2.255.255.0.32", "32", "2", "-4", "1722512"],
        ["0.0.0.2.255.255.0.34", "34", "2", "-4", "1097429"],
        ["0.0.0.2.255.255.0.36", "36", "2", "-4", "1271089"],
        ["0.0.0.2.255.255.0.38", "38", "2", "-4", "1271089"],
        ["0.0.0.255.255.255.0.4", "4", "2", "-2", "261"],
        ["0.0.0.255.255.255.0.5", "5", "2", "-2", "662"],
        ["0.0.0.255.255.255.0.9", "9", "2", "-2", "75"],
        ["0.0.0.255.255.255.0.18", "18", "2", "-1", "6107"],
        ["0.0.0.255.255.255.0.19", "19", "2", "-1", "4497"],
        ["0.0.0.255.255.255.0.20", "20", "2", "-1", "10460"],
        ["0.0.0.255.255.255.0.22", "22", "2", "-1", "4126"],
        ["0.0.0.255.255.255.0.24", "24", "2", "-2", "324"],
        ["0.0.0.255.255.255.0.32", "32", "2", "-4", "6653776"],
        ["0.0.0.255.255.255.0.34", "34", "2", "-4", "3778364"],
        ["0.0.0.255.255.255.0.36", "36", "2", "-4", "5141093"],
        ["0.0.0.255.255.255.0.38", "38", "2", "-4", "5141093"],
        ["0.0.255.255.255.255.0.4", "4", "2", "-2", "261"],
        ["0.0.255.255.255.255.0.5", "5", "2", "-2", "662"],
        ["0.0.255.255.255.255.0.19", "19", "2", "-1", "4497"],
        ["0.0.255.255.255.255.0.20", "20", "2", "-1", "10460"],
        ["0.0.255.255.255.255.0.36", "36", "2", "-4", "5141093"],
        ["0.0.255.255.255.255.0.38", "38", "2", "-4", "5141093"],
        ["0.1.64.4.255.2.1.0", "256", "2", "-1", "260"],
        ["0.1.64.4.255.2.1.1", "257", "2", "-1", "369"],
        ["0.4.0.0.255.255.0.7", "7", "2", "-1", "16"],
        ["0.4.0.0.255.255.0.8", "8", "2", "-1", "0"],
        ["0.4.0.1.255.255.0.7", "7", "2", "-1", "16"],
        ["0.4.0.1.255.255.0.8", "8", "2", "-1", "0"],
        ["0.4.0.2.255.255.0.7", "7", "2", "-1", "10"],
        ["0.4.0.2.255.255.0.8", "8", "2", "-1", "1"],
    ],
    [],
    [],
]


@pytest.mark.parametrize(
    "string_table, discovery_result",
    [
        pytest.param(
            _STRING_TABLE,
            [
                Service(item="1.1 Phase 1"),
                Service(item="1.1 Phase 2"),
                Service(item="1.1 Phase 3"),
            ],
            id="A service is discovered for every phase from the input.",
        ),
        pytest.param(
            [[], [], [], [], [], []],
            [],
            id="If there are no phases in the input, no Service is discovered.",
        ),
    ],
)
def test_discover_bluenet2_powerrail_phases(
    string_table: list[StringTable],
    discovery_result: Sequence[Service],
) -> None:
    assert (
        list(
            discover_bluenet2_powerrail_phases(
                parse_bluenet2_powerrail(string_table),
            )
        )
        == discovery_result
    )


@pytest.mark.parametrize(
    "string_table, item, check_result",
    [
        pytest.param(
            _STRING_TABLE,
            "1.1 Phase 1",
            [
                Result(state=State.OK, summary="Name: Phase 1"),
                Result(state=State.OK, summary="Voltage: 234.2 V"),
                Metric("voltage", 234.24),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Current: 1.0 A"),
                Metric("current", 0.99),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Power: 182.6 W"),
                Metric("power", 182.60000000000002),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Apparent Power: 230.9 VA"),
                Metric("appower", 230.9),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Frequency: 50.0 hz"),
                Metric("frequency", 49.99),
                Result(state=State.OK, summary="OK"),
            ],
            id="Everything is OK.",
        ),
        pytest.param(
            [
                [["1.1", "\x00\x00\x00ÿÿÿ\x00\x00", "Inlet 1", "Inlet 1"]],
                [
                    ["1.1.1", "\x00\x00\x00\x00ÿÿ\x00\x00", "Phase 1", "Phase 1"],
                ],
                [],
                [
                    ["0.0.0.0.255.255.0.1", "1", "42", "-2", "23424"],
                    ["0.0.0.0.255.255.0.4", "4", "2", "-2", "99"],
                    ["0.0.0.0.255.255.0.5", "5", "2", "-2", "261"],
                    ["0.0.0.0.255.255.0.17", "17", "2", "-3", "-791"],
                    ["0.0.0.0.255.255.0.18", "18", "2", "-1", "2309"],
                    ["0.0.0.0.255.255.0.19", "19", "2", "-1", "1826"],
                    ["0.0.0.0.255.255.0.20", "20", "2", "-1", "4707"],
                    ["0.0.0.0.255.255.0.22", "22", "2", "-1", "-1413"],
                    ["0.0.0.0.255.255.0.23", "23", "2", "-2", "4999"],
                ],
                [],
                [],
            ],
            "1.1 Phase 1",
            [
                Result(state=State.OK, summary="Name: Phase 1"),
                Result(state=State.OK, summary="Voltage: 234.2 V"),
                Metric("voltage", 234.24),
                Result(state=State.WARN, summary="warning"),
                Result(state=State.OK, summary="Current: 1.0 A"),
                Metric("current", 0.99),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Power: 182.6 W"),
                Metric("power", 182.60000000000002),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Apparent Power: 230.9 VA"),
                Metric("appower", 230.9),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Frequency: 50.0 hz"),
                Metric("frequency", 49.99),
                Result(state=State.OK, summary="OK"),
            ],
            id="The voltage value has the warning state, so the result of the check is WARN.",
        ),
        pytest.param(
            [
                [["1.1", "\x00\x00\x00ÿÿÿ\x00\x00", "Inlet 1", "Inlet 1"]],
                [
                    ["1.1.1", "\x00\x00\x00\x00ÿÿ\x00\x00", "Phase 1", "Phase 1"],
                ],
                [],
                [
                    ["0.0.0.0.255.255.0.1", "1", "39", "-2", "23424"],
                    ["0.0.0.0.255.255.0.4", "4", "2", "-2", "99"],
                    ["0.0.0.0.255.255.0.5", "5", "2", "-2", "261"],
                    ["0.0.0.0.255.255.0.17", "17", "2", "-3", "-791"],
                    ["0.0.0.0.255.255.0.18", "18", "2", "-1", "2309"],
                    ["0.0.0.0.255.255.0.19", "19", "2", "-1", "1826"],
                    ["0.0.0.0.255.255.0.20", "20", "2", "-1", "4707"],
                    ["0.0.0.0.255.255.0.22", "22", "2", "-1", "-1413"],
                    ["0.0.0.0.255.255.0.23", "23", "2", "-2", "4999"],
                ],
                [],
                [],
            ],
            "1.1 Phase 1",
            [
                Result(state=State.OK, summary="Name: Phase 1"),
                Result(state=State.OK, summary="Voltage: 234.2 V"),
                Metric("voltage", 234.24),
                Result(state=State.CRIT, summary="high"),
                Result(state=State.OK, summary="Current: 1.0 A"),
                Metric("current", 0.99),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Power: 182.6 W"),
                Metric("power", 182.60000000000002),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Apparent Power: 230.9 VA"),
                Metric("appower", 230.9),
                Result(state=State.OK, summary="OK"),
                Result(state=State.OK, summary="Frequency: 50.0 hz"),
                Metric("frequency", 49.99),
                Result(state=State.OK, summary="OK"),
            ],
            id="The voltage value has the high state, so the result of the check is CRIT.",
        ),
    ],
)
def test_check_bluenet2_powerrail_phases(
    string_table: list[StringTable],
    item: str,
    check_result: Sequence[Result | Metric],
) -> None:
    assert (
        list(
            check_bluenet2_powerrail_phases(
                item=item,
                params={},
                section=parse_bluenet2_powerrail(string_table),
            )
        )
        == check_result
    )
