#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ucs_bladecenter.server_side_calls.special_agent import (
    special_agent_ucs_bladecenter,
)
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="address"),
)


@pytest.mark.parametrize(
    "raw_params, expected_command",
    [
        pytest.param(
            {"username": "username", "password": Secret(23), "certificate_validation": False},
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "username",
                    "-p",
                    Secret(23).unsafe(),
                    "--no-cert-check",
                    "address",
                ]
            ),
            id="with no certificate validation",
        ),
        pytest.param(
            {"username": "username", "password": Secret(23), "certificate_validation": True},
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "username",
                    "-p",
                    Secret(23).unsafe(),
                    "--cert-server-name",
                    "hostname",
                    "address",
                ]
            ),
            id="with certificate validation",
        ),
    ],
)
def test_special_agent_ucs_bladecenter_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_ucs_bladecenter(raw_params, HOST_CONFIG)) == [expected_command]
