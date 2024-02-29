#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.server_side_calls.cisco_meraki import special_agent_cisco_meraki
from cmk.server_side_calls.v1 import HostConfig, HTTPProxy, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)

HTTP_PROXIES = {"my_proxy": HTTPProxy(id="my_proxy", name="My Proxy", url="proxy.com")}


@pytest.mark.parametrize(
    "params, expected_args",
    [
        pytest.param(
            {
                "api_key": Secret(0),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                    ]
                )
            ],
            id="Default arguments",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": (
                    "url",
                    "abc:8567",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--proxy",
                        "abc:8567",
                    ]
                )
            ],
            id="Proxy settings, url proxy",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": (
                    "environment",
                    "environment",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--proxy",
                        "FROM_ENVIRONMENT",
                    ]
                )
            ],
            id="Proxy settings, environment proxy",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": (
                    "no_proxy",
                    None,
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--proxy",
                        "NO_PROXY",
                    ]
                )
            ],
            id="Proxy settings, no proxy",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": (
                    "global",
                    "my_proxy",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--proxy",
                        "proxy.com",
                    ]
                )
            ],
            id="Proxy settings, global proxy",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": (
                    "global",
                    "test_proxy",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--proxy",
                        "FROM_ENVIRONMENT",
                    ]
                )
            ],
            id="Proxy settings, global proxy not found in global config",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "sections": ["sec1", "sec2"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--sections",
                        "sec1",
                        "sec2",
                    ]
                )
            ],
            id="Sections",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "orgs": ["org1", "org2"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        Secret(0),
                        "--orgs",
                        "org1",
                        "org2",
                    ]
                )
            ],
            id="Organisation IDs",
        ),
    ],
)
def test_aws_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[SpecialAgentCommand],
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_cisco_meraki(params, HOST_CONFIG, HTTP_PROXIES)) == expected_args
