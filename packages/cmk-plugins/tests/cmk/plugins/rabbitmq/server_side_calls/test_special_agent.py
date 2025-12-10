#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.rabbitmq.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand


def test_agent_rabbitmq() -> None:
    params = {
        "user": "username",
        "password": Secret(1),
        "sections": ["nodes", "cluster"],
        "protocol": "https",
    }
    assert list(commands_function(Params.model_validate(params), HostConfig(name="testhost"))) == [
        SpecialAgentCommand(
            command_arguments=[
                "-P",
                "https",
                "-m",
                "nodes,cluster",
                "--user",
                "username",
                "--password-id",
                Secret(1),
                "--hostname",
                "testhost",
            ]
        ),
    ]
