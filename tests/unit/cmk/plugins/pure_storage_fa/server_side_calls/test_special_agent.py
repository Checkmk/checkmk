#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.pure_storage_fa.server_side_calls.special_agent import (
    special_agent_pure_storage_fa,
)
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    "params, host_ip_address, hostname, expected_arguments",
    [
        pytest.param(
            {
                "timeout": 1,
                "ssl": ("hostname", None),
                "api_token": Secret(23),
            },
            "1.2.3.4",
            "host",
            [
                "--timeout",
                "1",
                "--cert-server-name",
                "host",
                "--api-token",
                Secret(23).unsafe(),
                "1.2.3.4",
            ],
            id="Available timeout and ssl True and stored api token and hostip available",
        ),
        pytest.param(
            {
                "ssl": ("custom_hostname", "something_else"),
                "api_token": Secret(23),
            },
            "1.2.3.4",
            "host",
            [
                "--cert-server-name",
                "something_else",
                "--api-token",
                Secret(23).unsafe(),
                "1.2.3.4",
            ],
            id="No timeout and ssl custom and hostip available",
        ),
    ],
)
def test_commands_function(
    params: Mapping[str, object],
    host_ip_address: str,
    hostname: str,
    expected_arguments: Sequence[str | Secret],
) -> None:
    assert list(
        special_agent_pure_storage_fa(
            params,
            HostConfig(
                name=hostname,
                alias="host",
                ipv4_config=IPv4Config(address=host_ip_address),
            ),
        )
    ) == [SpecialAgentCommand(command_arguments=expected_arguments)]
