#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.ruckus_spot.server_side_calls.special_agent import special_agent_ruckus_spot
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="address"),
)


@pytest.mark.parametrize(
    ["raw_params", "expected_command"],
    [
        pytest.param(
            {
                "venueid": "venueID",
                "api_key": Secret(23),
                "port": 8443,
                "address": ("use_host_address", None),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "address:8443",
                    "venueID",
                    Secret(23).unsafe(),
                    "--cert-server-name",
                    "hostname",
                ]
            ),
            id="Host adress and no cmk_agent",
        ),
        pytest.param(
            {
                "cmk_agent": {"port": 6556},
                "venueid": "venueID",
                "api_key": Secret(23),
                "port": 8443,
                "address": ("manual_address", "addresstest"),
            },
            SpecialAgentCommand(
                command_arguments=[
                    "addresstest:8443",
                    "venueID",
                    Secret(23).unsafe(),
                    "--agent_port",
                    "6556",
                ]
            ),
            id="Manual address and cmk_agent",
        ),
    ],
)
def test_special_agent_ruckus_spot_command_creation(
    raw_params: Mapping[str, object],
    expected_command: SpecialAgentCommand,
) -> None:
    assert list(special_agent_ruckus_spot(raw_params, HOST_CONFIG)) == [expected_command]
