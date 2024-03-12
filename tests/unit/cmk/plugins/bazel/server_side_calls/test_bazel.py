#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

# from cmk.plugins.bazel.lib.agent import agent_bazel_cache_main
from cmk.plugins.bazel.server_side_calls.special_agent import special_agent_bazel_cache
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="my_horst",
    ipv4_config=IPv4Config(address="17.1.10.93"),
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {
                "user": "username",
                "password": Secret(123),
                "host": "my_horst",
                "port": 9090,
                "protocol": "https",
                "no_cert_check": False,
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--host",
                        "my_horst",
                        "--user",
                        "username",
                        "--password",
                        Secret(123).unsafe(),
                        "--port",
                        "9090",
                        "--protocol",
                        "https",
                        "--no-cert-check",
                    ]
                )
            ],
            id="all params",
        ),
        pytest.param(
            {
                "host": "my_horst",
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--host",
                        "my_horst",
                        "--no-cert-check",
                    ]
                )
            ],
            id="minimal params",
        ),
    ],
)
def test_bazel_argument_parsing(
    params: Mapping[str, object],
    expected_result: Sequence[SpecialAgentCommand],
) -> None:
    assert list(special_agent_bazel_cache(params, HOST_CONFIG)) == expected_result
