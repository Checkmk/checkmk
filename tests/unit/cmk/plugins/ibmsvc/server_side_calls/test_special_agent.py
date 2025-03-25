#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ibmsvc.server_side_calls.special_agent import special_agent_ibmsvc
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "host_config", "expected_result"],
    [
        pytest.param(
            {
                "user": "user",
                "accept_any_hostkey": False,
                "infos": [
                    "lshost",
                    "lslicense",
                    "lsmdisk",
                ],
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "user",
                    "-i",
                    "lshost,lslicense,lsmdisk",
                    "1.2.3.4",
                ]
            ),
            id="do not accept any host key",
        ),
        pytest.param(
            {
                "user": "user",
                "accept_any_hostkey": True,
                "infos": [
                    "lssystemstats",
                    "lsportfc",
                    "lsenclosure",
                    "lsenclosurestats",
                    "lsarray",
                ],
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "user",
                    "-i",
                    "lssystemstats,lsportfc,lsenclosure,lsenclosurestats,lsarray",
                    "--accept-any-hostkey",
                    "1.2.3.4",
                ]
            ),
            id="accept any host key",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_ibmsvc(
            raw_params,
            host_config,
        )
    ) == [expected_result]
