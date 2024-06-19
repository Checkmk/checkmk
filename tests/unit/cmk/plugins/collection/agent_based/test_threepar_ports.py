#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_ports import (
    check_3par_ports,
    discover_3par_ports,
    parse_3par_ports,
    THREEPAR_PORTS_DEFAULT_LEVELS,
)

STRING_TABLE = [
    [
        '{"total":24,"members":[{"portPos":{"node":0,"slot":0,"cardPort":1},"mode":3,"linkState":4,"portWWN":"943FC9606F9C","type":2,"protocol":1,"label":"DP-1"},{"portPos":{"node":0,"slot":0,"cardPort":1},"mode":3,"linkState":4,"portWWN":"943FC9606F9C","type":2,"protocol":6,"label":"DP-1"}]}'
    ]
]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(item="FC Node 0 Slot 0 Port 1"),
                Service(item="NVMe Node 0 Slot 0 Port 1"),
            ],
            id="For every port that doesn't have a type of 3, a Service is discovered.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 3,"protocol": 6,"label": "DP-1"}]}'
                ]
            ],
            [],
            id="If a port has a type of 3, no Service is discovered.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 1,"protocol": 7,"label": "DP-1"}]}'
                ]
            ],
            [],
            id="If the port protocol is unknown, no Service is discovered.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discover_3par_ports(
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert list(discover_3par_ports(parse_3par_ports(section))) == expected_discovery_result


@pytest.mark.parametrize(
    "section, item, expected_check_result",
    [
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1"}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.OK, summary="READY"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
            ],
            id="If the port has a state of READY or NONPARTICIPATE and no failoverState is present, the result is OK.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 12,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1"}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.WARN, summary="IDLE_FOR_RESET"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
            ],
            id="The port has one of the warning states, the result is WARN.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 5,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1"}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.CRIT, summary="LOSS_SYNC"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
            ],
            id="If the port has a state of LOSS_SYNC or ERROR_STATE, the result is CRIT.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1","failoverState": 1}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.OK, summary="READY"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
                Result(state=State.OK, summary="Failover: NONE"),
            ],
            id="If the failover state of the port is NONE, the result is OK.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1","failoverState": 7}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.OK, summary="READY"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
                Result(state=State.WARN, summary="Failover: FAILBACK_PENDING"),
            ],
            id="If the failover state of the port is FAILBACK_PENDING, the result is WARN.",
        ),
        pytest.param(
            [
                [
                    '{"total": 24,"members": [{"portPos": {"node": 0,"slot": 0,"cardPort": 1},"mode": 3,"linkState": 4,"portWWN": "943FC9606F9C","type": 1,"protocol": 1,"label": "DP-1","failoverState": 5}]}'
                ]
            ],
            "FC Node 0 Slot 0 Port 1",
            [
                Result(state=State.OK, summary="Label: DP-1"),
                Result(state=State.OK, summary="READY"),
                Result(state=State.OK, summary="portWWN: 943FC9606F9C"),
                Result(state=State.OK, summary="Mode: INITIATOR"),
                Result(state=State.CRIT, summary="Failover: ACTIVE_DOWN"),
            ],
            id="If the failover state of the port is none of the two above, the result is CRIT.",
        ),
    ],
)
def test_check_3par_ports(
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_3par_ports(
                item=item,
                params=THREEPAR_PORTS_DEFAULT_LEVELS,
                section=parse_3par_ports(section),
            )
        )
        == expected_check_result
    )
