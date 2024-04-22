#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.jenkins.server_side_calls.jenkins import special_agent_jenkins
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "user": "username",
                "password": Secret(0),
                "instance": "test",
                "protocol": "https",
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "-P",
                        "https",
                        "-u",
                        "username",
                        "-s",
                        Secret(0).unsafe(),
                        "test",
                    ]
                )
            ],
            id="only required params",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(0),
                "instance": "test",
                "protocol": "https",
                "port": 442,
                "path": "path",
                "sections": ["instance", "jobs", "nodes", "queue"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "-P",
                        "https",
                        "-u",
                        "username",
                        "-s",
                        Secret(0).unsafe(),
                        "--path",
                        "path",
                        "-m",
                        "instance jobs nodes queue",
                        "-p",
                        "442",
                        "test",
                    ]
                )
            ],
            id="all params",
        ),
    ],
)
def test_agent_jenkins_arguments_password_store(
    params: Mapping[str, object], expected_result: Sequence[SpecialAgentCommand]
) -> None:
    assert list(special_agent_jenkins(params, HOST_CONFIG)) == expected_result
