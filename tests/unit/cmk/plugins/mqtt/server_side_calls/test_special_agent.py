#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.mqtt.server_side_calls.special_agent import special_agent_mqtt
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="host",
    ipv4_config=IPv4Config(address="address"),
)


@pytest.mark.parametrize(
    "raw_params, expected_args",
    [
        pytest.param(
            {
                "username": "asd",
                "password": Secret(33),
                "address": "addr",
                "port": 1337,
                "client_id": "ding",
                "protocol": "MQTTv5",
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--client-id",
                    "ding",
                    "--password",
                    Secret(33).unsafe(),
                    "--port",
                    "1337",
                    "--protocol",
                    "MQTTv5",
                    "--username",
                    "asd",
                    "addr",
                ]
            ),
            id="all_arguments",
        ),
        pytest.param(
            {
                "password": Secret(id=1, pass_safely=True),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--password",
                    Secret(id=1, format="%s", pass_safely=False),
                    "address",
                ]
            ),
            id="with_password_store",
        ),
        pytest.param(
            {},
            SpecialAgentCommand(command_arguments=["address"]),
            id="minimal_arguments",
        ),
    ],
)
def test_mqtt_argument_parsing(
    raw_params: Mapping[str, object],
    expected_args: SpecialAgentCommand,
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_mqtt(raw_params, HOST_CONFIG)) == [expected_args]
