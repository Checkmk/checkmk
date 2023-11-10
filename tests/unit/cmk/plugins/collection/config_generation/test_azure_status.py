#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.config_generation.azure_status import special_agent_azure_status
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname", address="0.0.0.1", alias="host_alias", ip_family=IPAddressFamily.IPv4
)


def test_azure_status_argument_parsing() -> None:
    param_dict = {"regions": ["eastus", "centralus", "northcentralus"]}
    params = special_agent_azure_status.parameter_parser(param_dict)
    commands = list(special_agent_azure_status.commands_function(params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0] == SpecialAgentCommand(
        command_arguments=["eastus", "centralus", "northcentralus"]
    )
