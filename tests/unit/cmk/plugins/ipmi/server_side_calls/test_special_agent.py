#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ipmi.server_side_calls.special_agent import special_agent_ipmi_sensors
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
                "agent": (
                    "freeipmi",
                    {
                        "username": "user",
                        "password": Secret(23),
                        "privilege_lvl": "user",
                    },
                ),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "1.2.3.4",
                    "user",
                    Secret(23).unsafe(),
                    "freeipmi",
                    "user",
                    "--output_sensor_state",
                ]
            ),
            id="freeipmi with mandatory args only and explicit password",
        ),
        pytest.param(
            {
                "agent": (
                    "freeipmi",
                    {
                        "username": "user",
                        "ipmi_driver": "driver",
                        "password": Secret(23),
                        "privilege_lvl": "user",
                        "sdr_cache_recreate": True,
                        "interpret_oem_data": True,
                        "output_sensor_state": False,
                    },
                ),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "1.2.3.4",
                    "user",
                    Secret(23).unsafe(),
                    "freeipmi",
                    "user",
                    "--driver",
                    "driver",
                    "--sdr_cache_recreate",
                    "--interpret_oem_data",
                ]
            ),
            id="freeipmi with optional args",
        ),
        pytest.param(
            {
                "agent": (
                    "ipmitool",
                    {
                        "username": "user",
                        "password": Secret(23),
                        "privilege_lvl": "administrator",
                        "intf": "lanplus",
                    },
                ),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "1.2.3.4",
                    "user",
                    Secret(23).unsafe(),
                    "ipmitool",
                    "administrator",
                    "--intf",
                    "lanplus",
                ]
            ),
            id="ipmitool with optional arg",
        ),
    ],
)
def test_special_agent_ipmi_sensors_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_ipmi_sensors(raw_params, HOST_CONFIG)) == [expected_command]
