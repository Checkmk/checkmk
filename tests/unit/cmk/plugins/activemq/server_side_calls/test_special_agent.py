#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.activemq.server_side_calls.special_agent import special_agent_activemq
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "expected_result"],
    [
        pytest.param(
            {
                "servername": "server",
                "port": 123,
                "protocol": "http",
                "use_piggyback": True,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "server",
                    "123",
                    "--protocol",
                    "http",
                    "--piggyback",
                ]
            ),
            id="without credentials",
        ),
        pytest.param(
            {
                "servername": "server",
                "port": 123,
                "protocol": "http",
                "use_piggyback": False,
                "basicauth": {
                    "username": "user",
                    "password": Secret(0),
                },
            },
            SpecialAgentCommand(
                command_arguments=[
                    "server",
                    "123",
                    "--protocol",
                    "http",
                    "--username",
                    "user",
                    "--password",
                    Secret(0).unsafe(),
                ]
            ),
            id="with credentials",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_activemq(
            raw_params,
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [expected_result]
