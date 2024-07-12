#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.siemens_plc.server_side_calls.special_agent import special_agent_siemens_plc
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "expected_result"],
    [
        pytest.param(
            {
                "devices": [
                    {
                        "slot": 2,
                        "tcp_port": 102,
                        "values": [],
                        "host_name": "device1",
                        "host_address": "host",
                        "rack": 2,
                    },
                    {
                        "slot": 1,
                        "tcp_port": 22,
                        "values": [],
                        "host_name": "device2",
                        "host_address": "hostaddress",
                        "rack": 2,
                    },
                ],
                "values": [],
                "timeout": 30,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--timeout",
                    "30",
                    "--hostspec",
                    "device1;host;2;2;102",
                    "--hostspec",
                    "device2;hostaddress;2;1;22",
                ]
            ),
            id="without values",
        ),
        pytest.param(
            {
                "devices": [
                    {
                        "slot": 2,
                        "tcp_port": 102,
                        "values": [
                            {
                                "address": 1.2,
                                "area": (
                                    "db",
                                    1,
                                ),
                                "data_type": (
                                    "dint",
                                    None,
                                ),
                                "id": "id1",
                                "value_type": "unclassified",
                            },
                            {
                                "address": 1.3,
                                "area": (
                                    "merker",
                                    None,
                                ),
                                "data_type": (
                                    "real",
                                    None,
                                ),
                                "id": "id2",
                                "value_type": "seconds_since_service",
                            },
                        ],
                        "host_name": "device1",
                        "host_address": "host",
                        "rack": 2,
                    },
                    {
                        "slot": 1,
                        "tcp_port": 22,
                        "values": [],
                        "host_name": "device2",
                        "host_address": "hostaddress",
                        "rack": 2,
                    },
                ],
                "values": [
                    {
                        "address": 2.5,
                        "area": (
                            "timer",
                            None,
                        ),
                        "data_type": (
                            "bit",
                            None,
                        ),
                        "id": "t1",
                        "value_type": "temp",
                    },
                    {
                        "address": 3.4,
                        "area": (
                            "counter",
                            None,
                        ),
                        "data_type": (
                            "str",
                            2,
                        ),
                        "id": "s1",
                        "value_type": "text",
                    },
                ],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--hostspec",
                    "device1;host;2;2;102;timer,2.5,bit,temp,t1;counter,3.4,str:2,text,s1;db:1,1.2,dint,None,id1;merker,1.3,real,seconds_since_service,id2",
                    "--hostspec",
                    "device2;hostaddress;2;1;22;timer,2.5,bit,temp,t1;counter,3.4,str:2,text,s1",
                ]
            ),
            id="with values",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_siemens_plc(
            raw_params,
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [expected_result]
