#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.plugins.jolokia.server_side_calls.special_agent import special_agent_jolokia
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="host",
    ipv4_config=IPv4Config(address="address"),
)


@pytest.mark.parametrize(
    ["raw_params", "expected_args"],
    [
        pytest.param(
            {},
            SpecialAgentCommand(
                command_arguments=[
                    "--server",
                    "address",
                ]
            ),
            id="without parameters",
        ),
        pytest.param(
            {"port": 8080},
            SpecialAgentCommand(
                command_arguments=[
                    "--server",
                    "address",
                    "--port",
                    "8080",
                ]
            ),
            id="with port value",
        ),
        pytest.param(
            {"instance": "monitor", "port": 8080},
            SpecialAgentCommand(
                command_arguments=[
                    "--server",
                    "address",
                    "--port",
                    "8080",
                    "--instance",
                    "monitor",
                ]
            ),
            id="with instance and port values",
        ),
        pytest.param(
            {
                "login": {
                    "user": "userID",
                    "password": Secret(23),
                    "mode": "basic",
                },
                "port": 8080,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--server",
                    "address",
                    "--port",
                    "8080",
                    "--user",
                    "userID",
                    "--password",
                    Secret(23).unsafe(),
                    "--mode",
                    "basic",
                ]
            ),
            id="explicit password",
        ),
        pytest.param(
            {
                "login": {
                    "user": "userID",
                    "password": Secret(id=1),
                    "mode": "basic",
                },
                "port": 8080,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--server",
                    "address",
                    "--port",
                    "8080",
                    "--user",
                    "userID",
                    "--password",
                    Secret(id=1).unsafe(),
                    "--mode",
                    "basic",
                ]
            ),
            id="password from the store",
        ),
    ],
)
def test_jolokia_argument_parsing(
    raw_params: Mapping[str, object],
    expected_args: SpecialAgentCommand,
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_jolokia(raw_params, HOST_CONFIG)) == [expected_args]
