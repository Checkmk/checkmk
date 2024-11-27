#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.splunk.server_side_calls.special_agent import special_agent_splunk
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand
from cmk.server_side_calls.v1._utils import Secret


def test_special_agent_splunk_command_creation() -> None:
    assert list(
        special_agent_splunk(
            {
                "user": "username",
                "password": Secret(23),
                "infos": ["jobs", "health", "alerts"],
                "protocol": "https",
            },
            HostConfig(
                name="testhost",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [
        SpecialAgentCommand(
            command_arguments=[
                "-P",
                "https",
                "-m",
                "jobs health alerts",
                "-u",
                "username",
                "-s",
                Secret(23).unsafe(),
                "testhost",
            ]
        )
    ]
