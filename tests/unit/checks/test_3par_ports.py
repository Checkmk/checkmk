#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [
    [
        '{"total":24,"members":[{"portPos":{"node":0,"slot":0,"cardPort":1},"mode":3,"linkState":4,"portWWN":"943FC9606F9C","type":2,"protocol":1,"label":"DP-1"},{"portPos":{"node":0,"slot":0,"cardPort":1},"mode":3,"linkState":4,"portWWN":"943FC9606F9C","type":2,"protocol":6,"label":"DP-1"}]}'
    ]
]

THREEPAR_PORTS_DEFAULT_LEVELS = {
    "1_link": 1,
    "2_link": 1,
    "3_link": 1,
    "4_link": 0,
    "5_link": 2,
    "6_link": 2,
    "7_link": 1,
    "8_link": 0,
    "9_link": 1,
    "10_link": 1,
    "11_link": 1,
    "12_link": 1,
    "13_link": 1,
    "14_link": 1,
    "1_fail": 0,
    "2_fail": 2,
    "3_fail": 2,
    "4_fail": 2,
    "5_fail": 2,
    "6_fail": 2,
    "7_fail": 1,
}


@pytest.fixture(name="check")
def _3par_ports_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("3par_ports")]


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
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    parse_3par = fix_register.agent_sections[SectionName("3par_ports")].parse_function
    assert list(check.discovery_function(parse_3par(section))) == expected_discovery_result


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
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    item: str,
    expected_check_result: Sequence[Result],
) -> None:
    parse_3par = fix_register.agent_sections[SectionName("3par_ports")].parse_function
    assert (
        list(
            check.check_function(
                item=item,
                params=THREEPAR_PORTS_DEFAULT_LEVELS,
                section=parse_3par(section),
            )
        )
        == expected_check_result
    )
