#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.smb.server_side_calls.special_agent import special_agent_smb_share
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand
from cmk.server_side_calls.v1._utils import Secret

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


@pytest.mark.parametrize(
    "raw_params, expected_command",
    [
        pytest.param(
            {
                "authentication": {"username": "user", "password": Secret(23)},
                "patterns": [],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "testhost",
                    "1.2.3.4",
                    "--username",
                    "user",
                    "--password",
                    Secret(23).unsafe(),
                ]
            ),
            id="explicit_password_no_ip",
        ),
        pytest.param(
            {
                "authentication": {"username": "user", "password": Secret(23)},
                "ip_address": "2.3.4",
                "patterns": [],
                "recursive": True,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "testhost",
                    "2.3.4",
                    "--username",
                    "user",
                    "--password",
                    Secret(23).unsafe(),
                    "--recursive",
                ]
            ),
            id="explicit_password_with_ip",
        ),
    ],
)
def test_special_agent_smb_share_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_smb_share(raw_params, HOST_CONFIG)) == [expected_command]
