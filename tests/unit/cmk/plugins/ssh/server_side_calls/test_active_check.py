#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ssh.server_side_calls.active_check import commands_function, Params
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config


@pytest.mark.parametrize(
    ["params", "expected_command"],
    [
        pytest.param(
            {},
            ActiveCheckCommand(
                service_description="SSH",
                command_arguments=["-H", "1.2.3.4"],
            ),
            id="minimal configuration",
        ),
        pytest.param(
            {
                "description": "abc",
                "port": 4587,
                "timeout": 120,
                "remote_version": "OpenSSH_8.2p1",
                "remote_protocol": "2.0",
            },
            ActiveCheckCommand(
                service_description="SSH abc",
                command_arguments=[
                    "-H",
                    "1.2.3.4",
                    "-t",
                    "120",
                    "-p",
                    "4587",
                    "-r",
                    "OpenSSH_8.2p1",
                    "-P",
                    "2.0",
                ],
            ),
            id="full configuration",
        ),
    ],
)
def test_commands_function(
    params: Mapping[str, object],
    expected_command: ActiveCheckCommand,
) -> None:
    assert list(
        commands_function(
            Params.model_validate(params),
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [expected_command]
