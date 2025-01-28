#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.plugins.vsphere.server_side_calls.special_agent import special_agent_vsphere
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="host",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


@pytest.mark.parametrize(
    ["raw_params", "expected_args"],
    [
        pytest.param(
            {
                "tcp_port": 443,
                "direct": "host_system",
                "skip_placeholder_vms": True,
                "ssl": ("deactivated", None),
                "secret": Secret(23),
                "spaces": "cut",
                "user": "username",
                "snapshots_on_host": False,
                "infos": ["hostsystem", "virtualmachine", "datastore", "counters"],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-p",
                    "443",
                    "-u",
                    "username",
                    f"-s={Secret(23).unsafe()}",
                    "-i",
                    "hostsystem,virtualmachine,datastore,counters",
                    "--direct",
                    "--hostname",
                    "host",
                    "-P",
                    "--spaces",
                    "cut",
                    "--no-cert-check",
                    "1.2.3.4",
                ],
            ),
            id="with explicit password",
        ),
        pytest.param(
            {
                "tcp_port": 443,
                "host_pwr_display": None,
                "vm_pwr_display": None,
                "direct": "host_system",
                "vm_piggyname": "alias",
                "skip_placeholder_vms": True,
                "ssl": ("hostname", None),
                "secret": Secret(id=1, pass_safely=True),
                "spaces": "cut",
                "user": "username",
                "snapshots_on_host": False,
                "infos": ["hostsystem", "virtualmachine", "datastore", "counters"],
            },
            SpecialAgentCommand(
                command_arguments=[
                    "-p",
                    "443",
                    "-u",
                    "username",
                    f"-s={Secret(id=1, format="%s", pass_safely=False)}",
                    "-i",
                    "hostsystem,virtualmachine,datastore,counters",
                    "--direct",
                    "--hostname",
                    "host",
                    "-P",
                    "--spaces",
                    "cut",
                    "--vm_piggyname",
                    "alias",
                    "--cert-server-name",
                    "host",
                    "1.2.3.4",
                ],
            ),
            id="with store password",
        ),
    ],
)
def test_vsphere_argument_parsing(
    raw_params: Mapping[str, object],
    expected_args: SpecialAgentCommand,
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_vsphere(raw_params, HOST_CONFIG)) == [expected_args]
