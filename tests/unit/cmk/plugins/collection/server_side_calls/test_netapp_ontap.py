#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.netapp.server_side_calls.netapp_ontap import special_agent_netapp_ontap
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="testhost",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


@pytest.mark.parametrize(
    "params, expected_args",
    [
        pytest.param(
            {
                "username": "user",
                "password": Secret(0),
                "no_cert_check": True,
                "fetched_resources": ["node", "fan"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--hostname",
                        "0.0.0.1",
                        "--username",
                        "user",
                        "--password",
                        Secret(0).unsafe(),
                        "--fetched-resources",
                        "node",
                        "fan",
                        "--no-cert-check",
                    ]
                )
            ],
            id="Do not check certificate",
        ),
        pytest.param(
            {
                "username": "user",
                "password": Secret(0),
                "no_cert_check": False,
                "fetched_resources": ["node"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--hostname",
                        "0.0.0.1",
                        "--username",
                        "user",
                        "--password",
                        Secret(0).unsafe(),
                        "--fetched-resources",
                        "node",
                        "--cert-server-name",
                        HOST_CONFIG.name,
                    ]
                )
            ],
            id="Check certificate",
        ),
        pytest.param(
            {
                "username": "user",
                "password": Secret(0),
                "no_cert_check": False,
                "fetched_resources": ["volumes"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--hostname",
                        "0.0.0.1",
                        "--username",
                        "user",
                        "--password",
                        Secret(0).unsafe(),
                        "--fetched-resources",
                        "volumes",
                        "--cert-server-name",
                        HOST_CONFIG.name,
                    ]
                )
            ],
            id="Exclude volume counters",
        ),
    ],
)
def test_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[SpecialAgentCommand],
) -> None:
    """Tests if all required arguments are present."""
    assert list(special_agent_netapp_ontap(params, HOST_CONFIG)) == expected_args
