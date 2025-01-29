#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.emcvnx.server_side_calls.special_agent import special_agent_emcvnx
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "host_config", "expected_result"],
    [
        pytest.param(
            {
                "infos": ["disks", "hba", "hwstatus"],
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "-i",
                    "disks,hba,hwstatus",
                    "1.2.3.4",
                ]
            ),
            id="no credentials",
        ),
        pytest.param(
            {
                "user": "user",
                "password": Secret(1),
                "infos": ["hwstatus"],
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "user",
                    "-p",
                    Secret(id=1, format="%s", pass_safely=False),
                    "-i",
                    "hwstatus",
                    "1.2.3.4",
                ]
            ),
            id="with credentials",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_emcvnx(
            raw_params,
            host_config,
        )
    ) == [expected_result]
