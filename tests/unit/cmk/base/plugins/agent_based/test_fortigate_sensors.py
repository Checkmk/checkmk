#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.fortigate_sensors import (
    check_fortigate_sensors,
    discover_fortigate_sensors,
    parse_fortigate_sensors,
)

from cmk.agent_based.v1.type_defs import StringTable

STRING_TABLE = [
    ["+VCC3", "3.311", "0"],
    ["NP6_1V15_1", "1.1533", "0"],
    ["PS1 Temp 2", "-1", "0"],
    ["PS1 Fan 1", "0", "1"],
    ["PS1 Status", "9", "1"],
    # arificially added line for full test coverage
    ["Both Zeroes", "0", "0"],
]


@pytest.mark.parametrize(
    "string_table, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [Service()],
            id="If the length of the input is 1 or more, a service with no item is discovered.",
        ),
        pytest.param(
            [
                ["PS1 Status", "9", "1"],
            ],
            [Service()],
            id="If there is only one faulty element, the service should still be discovered.",
        ),
        pytest.param(
            [["PS1 Fan 1", "0", "1"], ["NP6_1V15_1", "1.1533", "0"]],
            [Service()],
            id="If there are unusual faulty elements, the service should still discovery the service",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_fortigate_sensors(
    string_table: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_fortigate_sensors(parse_fortigate_sensors(string_table)))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    "string_table, expected_check_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Result(state=State.OK, summary="5 sensors"),
                Result(state=State.OK, summary="3 OK"),
                Result(state=State.OK, summary="2 with alarm"),
                Result(state=State.CRIT, summary="PS1 Fan 1"),
                Result(state=State.CRIT, summary="PS1 Status"),
            ],
            id="If one or more items have an alarm, the check state is CRIT.",
        ),
        pytest.param(
            [["PS1 Status", "9", "1"]],
            [
                Result(state=State.OK, summary="1 sensors"),
                Result(state=State.OK, summary="0 OK"),
                Result(state=State.OK, summary="1 with alarm"),
                Result(state=State.CRIT, summary="PS1 Status"),
            ],
            id="If the only item is faulty, the amount of ok items should be zero.",
        ),
        pytest.param(
            [],
            [Result(state=State.CRIT, summary="No sensors found")],
            id="If the service has been discovered, but no data is fetched anymore, the service should be CRIT.",
        ),
    ],
)
def test_check_fortigate_sensors(
    string_table: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_fortigate_sensors(
                section=parse_fortigate_sensors(string_table),
            )
        )
        == expected_check_result
    )
