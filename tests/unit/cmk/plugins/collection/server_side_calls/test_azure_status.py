#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.collection.server_side_calls.azure_status import special_agent_azure_status
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    ResolvedIPAddressFamily,
    SpecialAgentCommand,
)

HOST_CONFIG = HostConfig(
    name="hostname",
    resolved_ipv4_address="0.0.0.1",
    alias="host_alias",
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.IPV4,
        ipv4_address="0.0.0.1",
    ),
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
)


def test_azure_status_argument_parsing() -> None:
    param_dict = {"regions": ["eastus", "centralus", "northcentralus"]}
    commands = list(special_agent_azure_status(param_dict, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0] == SpecialAgentCommand(
        command_arguments=["eastus", "centralus", "northcentralus"]
    )
