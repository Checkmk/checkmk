#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.random.server_side_calls.special_agent import special_agent_random
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand


def test_special_agent_random_command_creation() -> None:
    assert list(
        special_agent_random(
            {"random": None},
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="address"),
            ),
        )
    ) == [SpecialAgentCommand(command_arguments=["host"])]
