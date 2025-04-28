#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.azure.server_side_calls.azure_status import special_agent_azure_status
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


def test_azure_status_argument_parsing() -> None:
    param_dict = {"regions": ["eastus", "centralus", "northcentralus"]}
    commands = list(special_agent_azure_status(param_dict, HOST_CONFIG))

    assert len(commands) == 1
    assert commands[0] == SpecialAgentCommand(
        command_arguments=["eastus", "centralus", "northcentralus"]
    )
