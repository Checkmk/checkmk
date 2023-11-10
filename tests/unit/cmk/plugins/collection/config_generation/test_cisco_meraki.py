#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.config_generation.cisco_meraki import special_agent_cisco_meraki
from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    PlainTextSecret,
    SpecialAgentCommand,
)

HOST_CONFIG = HostConfig(
    name="testhost",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
    ipv4address=None,
    ipv6address=None,
    additional_ipv4addresses=[],
    additional_ipv6addresses=[],
)

HTTP_PROXIES = {"my_proxy": HTTPProxy("my_proxy", "My Proxy", "proxy.com")}


@pytest.mark.parametrize(
    "params, expected_args",
    [
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                    ]
                )
            ],
            id="Default arguments",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "url",
                    "abc:8567",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                        "--proxy",
                        "abc:8567",
                    ]
                )
            ],
            id="Proxy settings, url proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "environment",
                    "environment",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                        "--proxy",
                        "FROM_ENVIRONMENT",
                    ]
                )
            ],
            id="Proxy settings, environment proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "no_proxy",
                    None,
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                        "--proxy",
                        "NO_PROXY",
                    ]
                )
            ],
            id="Proxy settings, no proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "global",
                    "my_proxy",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                        "--proxy",
                        "proxy.com",
                    ]
                )
            ],
            id="Proxy settings, global proxy",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "proxy": (
                    "global",
                    "test_proxy",
                ),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
                        "--proxy",
                        "FROM_ENVIRONMENT",
                    ]
                )
            ],
            id="Proxy settings, global proxy not found in global config",
        ),
        pytest.param(
            {
                "api_key": ("password", "my-api-key"),
                "sections": ["sec1", "sec2"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
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
                "api_key": ("password", "my-api-key"),
                "orgs": ["org1", "org2"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        PlainTextSecret(value="my-api-key"),
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
    parsed_params = special_agent_cisco_meraki.parameter_parser(params)
    assert (
        list(special_agent_cisco_meraki.commands_function(parsed_params, HOST_CONFIG, HTTP_PROXIES))
        == expected_args
    )
