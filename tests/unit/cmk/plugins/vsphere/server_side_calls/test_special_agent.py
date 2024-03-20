#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.vsphere.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["params", "expected_arguments"],
    [
        pytest.param(
            {
                "tcp_port": 443,
                "direct": True,
                "skip_placeholder_vms": True,
                "ssl": False,
                "secret": Secret(123),
                "spaces": "cut",
                "user": "username",
                "infos": ["hostsystem", "virtualmachine", "datastore", "counters"],
                "snapshots_on_host": False,
            },
            [
                "1.2.3.4",
                "-u",
                "username",
                "-s",
                Secret(123),
                "-i",
                "hostsystem,virtualmachine,datastore,counters",
                "--spaces",
                "cut",
                "-p",
                "443",
                "--direct",
                "--hostname",
                "host",
                "-P",
                "--no-cert-check",
            ],
        ),
        (
            {
                "tcp_port": 443,
                "host_pwr_display": None,
                "vm_pwr_display": None,
                "direct": True,
                "vm_piggyname": "alias",
                "skip_placeholder_vms": True,
                "ssl": False,
                "secret": Secret(42),
                "spaces": "cut",
                "user": "username",
                "infos": ["hostsystem", "virtualmachine", "datastore", "counters"],
                "snapshots_on_host": True,
            },
            [
                "1.2.3.4",
                "-u",
                "username",
                "-s",
                Secret(42),
                "-i",
                "hostsystem,virtualmachine,datastore,counters",
                "--spaces",
                "cut",
                "-p",
                "443",
                "--direct",
                "--hostname",
                "host",
                "-P",
                "--vm_piggyname",
                "alias",
                "--snapshots-on-host",
                "--no-cert-check",
            ],
        ),
    ],
)
def test_commands_function(
    params: Mapping[str, object],
    expected_arguments: Sequence[str | Secret],
) -> None:
    assert list(
        commands_function(
            Params.model_validate(params),
            HostConfig(
                name="host",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            {},
        )
    ) == [SpecialAgentCommand(command_arguments=expected_arguments)]
