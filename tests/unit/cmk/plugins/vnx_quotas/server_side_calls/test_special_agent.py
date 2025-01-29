#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.vnx_quotas.server_side_calls.special_agent import special_agent_vnx_quotas
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


@pytest.mark.parametrize(
    ["raw_params", "expected_command"],
    [
        pytest.param(
            {
                "user": "username",
                "password": Secret(23),
                "nas_db": "",
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "username",
                    "-p",
                    Secret(23).unsafe(),
                    "--nas-db",
                    "",
                    "1.2.3.4",
                ]
            ),
            id="with explicit password",
        ),
        pytest.param(
            {
                "user": "username",
                "password": Secret(id=1, pass_safely=True),
                "nas_db": "",
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-u",
                    "username",
                    "-p",
                    Secret(id=1, format="%s", pass_safely=False),
                    "--nas-db",
                    "",
                    "1.2.3.4",
                ]
            ),
            id="with password from store",
        ),
    ],
)
def test_special_agent_vnx_quotas_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_vnx_quotas(raw_params, HOST_CONFIG)) == [expected_command]
