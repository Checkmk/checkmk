#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.cisco_meraki.server_side_calls.agent_cisco_meraki import special_agent_cisco_meraki
from cmk.server_side_calls.v1 import (
    EnvProxy,
    HostConfig,
    IPv4Config,
    NoProxy,
    Secret,
    SpecialAgentCommand,
    URLProxy,
)

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


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
                        "--apikey-reference",
                        Secret(0),
                    ]
                )
            ],
            id="Default arguments",
        ),
        pytest.param(
            {
                "api_key": Secret(0),
                "proxy": URLProxy(url="abc:8567"),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        "--apikey-reference",
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
                "proxy": EnvProxy(),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        "--apikey-reference",
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
                "proxy": NoProxy(),
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        "--apikey-reference",
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
                "sections": ["licenses_overview", "device_statuses"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "testhost",
                        "--apikey-reference",
                        Secret(0),
                        "--sections",
                        "licenses-overview",
                        "device-statuses",
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
                        "--apikey-reference",
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
def test_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[SpecialAgentCommand],
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_cisco_meraki(params, HOST_CONFIG)) == expected_args
