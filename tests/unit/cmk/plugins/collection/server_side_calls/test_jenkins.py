#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.jenkins import special_agent_jenkins
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    PlainTextSecret,
    ResolvedIPAddressFamily,
    SpecialAgentCommand,
)

HOST_CONFIG = HostConfig(
    name="hostname",
    resolved_ipv4_address="0.0.0.1",
    alias="host_alias",
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.IPV4,
        ipv4_address="0.0.0.1",
    ),
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "user": "username",
                "password": ("password", "passwd"),
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
                        PlainTextSecret(value="passwd", format="%s"),
                        "test",
                    ]
                )
            ],
            id="only required params",
        ),
        pytest.param(
            {
                "user": "username",
                "password": ("password", "passwd"),
                "instance": "test",
                "protocol": "https",
                "port": 442,
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
                        PlainTextSecret(value="passwd", format="%s"),
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
    assert list(special_agent_jenkins(params, HOST_CONFIG, {})) == expected_result
