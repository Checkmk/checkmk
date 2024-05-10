#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.dns.server_side_calls.active_check import commands_function, Params
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config


@pytest.mark.parametrize(
    "params, expected_command",
    [
        pytest.param(
            {"hostname": "hostname"},
            ActiveCheckCommand(
                service_description="DNS hostname",
                command_arguments=["-H", "hostname", "-s", "1.2.3.4", "-L"],
            ),
            id="No params",
        ),
        pytest.param(
            {"hostname": "hostname", "server": "default DNS server", "timeout": 1},
            ActiveCheckCommand(
                service_description="DNS hostname",
                command_arguments=["-H", "hostname", "-L", "-t", "1"],
            ),
            id="Default DNS server",
        ),
        pytest.param(
            {
                "hostname": "hostname",
                "name": "check_name",
                "server": "some_dns_server",
                "expected_addresses_list": ("2.4.5.6", "2.4.5.7"),
                "expected_authority": True,
                "response_time": (100.0, 200.0),
                "timeout": 10,
            },
            ActiveCheckCommand(
                service_description="check_name",
                command_arguments=[
                    "-H",
                    "hostname",
                    "-s",
                    "some_dns_server",
                    "-L",
                    "-a",
                    "2.4.5.6",
                    "-a",
                    "2.4.5.7",
                    "-A",
                    "-w",
                    "100.000000",
                    "-c",
                    "200.000000",
                    "-t",
                    "10",
                ],
            ),
            id="Custom params",
        ),
        pytest.param(
            {
                "hostname": "hostname",
                "expected_addresses_list": ["1.2.3.4", "C0FE::FE11"],
                "server": "127.0.0.53",
                "timeout": 10,
                "response_time": (1.0, 2.0),
                "expected_authority": True,
            },
            ActiveCheckCommand(
                service_description="DNS hostname",
                command_arguments=[
                    "-H",
                    "hostname",
                    "-s",
                    "127.0.0.53",
                    "-L",
                    "-a",
                    "1.2.3.4",
                    "-a",
                    "C0FE::FE11",
                    "-A",
                    "-w",
                    "1.000000",
                    "-c",
                    "2.000000",
                    "-t",
                    "10",
                ],
            ),
            id="Second custom params",
        ),
        pytest.param(
            {
                "hostname": "hostname",
                "server": None,
                "expect_all_addresses": False,
                "expected_addresses_list": ["1.2.3.4", "5.6.7.8"],
            },
            ActiveCheckCommand(
                service_description="DNS hostname",
                command_arguments=[
                    "-H",
                    "hostname",
                    "-s",
                    "1.2.3.4",
                    "-a",
                    "1.2.3.4",
                    "-a",
                    "5.6.7.8",
                ],
            ),
            id="Custom params with expect_all_addresses False",
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
                name="check",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [expected_command]
