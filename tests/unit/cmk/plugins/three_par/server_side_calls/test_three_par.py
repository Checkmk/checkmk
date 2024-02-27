#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.three_par.server_side_calls.three_par import special_agent_three_par
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    PlainTextSecret,
    ResolvedIPAddressFamily,
    SpecialAgentCommand,
    StoredSecret,
)

HOST_CONFIG = HostConfig(
    name="host",
    resolved_address="address",
    alias="alias",
    address_config=NetworkAddressConfig(
        ip_family=IPAddressFamily.IPV4,
    ),
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
)


@pytest.mark.parametrize(
    "params,result",
    [
        (
            {
                "user": "user",
                "password": ("password", "d1ng"),
                "port": 8080,
                "verify_cert": False,
                "values": ["x", "y"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--user",
                        "user",
                        "--password",
                        PlainTextSecret(value="d1ng"),
                        "--port",
                        "8080",
                        "--no-cert-check",
                        "--values",
                        "x,y",
                        "address",
                    ]
                )
            ],
        ),
        (
            {
                "user": "user",
                "password": ("password", "d1ng"),
                "port": 1234,
                "values": ["x", "y"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--user",
                        "user",
                        "--password",
                        PlainTextSecret(value="d1ng"),
                        "--port",
                        "1234",
                        "--no-cert-check",
                        "--values",
                        "x,y",
                        "address",
                    ]
                )
            ],
        ),
        (
            {
                "user": "user",
                "password": ("password", "d1ng"),
                "port": 8090,
                "verify_cert": True,
                "values": ["x", "y"],
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--user",
                        "user",
                        "--password",
                        PlainTextSecret(value="d1ng"),
                        "--port",
                        "8090",
                        "--values",
                        "x,y",
                        "address",
                    ]
                )
            ],
        ),
        (
            {
                "user": "user",
                "password": ("password", "d1ng"),
                "port": 500,
                "verify_cert": True,
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--user",
                        "user",
                        "--password",
                        PlainTextSecret(value="d1ng"),
                        "--port",
                        "500",
                        "address",
                    ]
                )
            ],
        ),
        (
            {
                "user": "user",
                "password": ("store", "pw-id"),
                "port": 8079,
                "verify_cert": True,
            },
            [
                SpecialAgentCommand(
                    command_arguments=[
                        "--user",
                        "user",
                        "--password",
                        StoredSecret(value="pw-id", format="%s"),
                        "--port",
                        "8079",
                        "address",
                    ]
                )
            ],
        ),
    ],
)
def test_3par(params: Mapping[str, object], result: Sequence[SpecialAgentCommand]) -> None:
    parsed_params = special_agent_three_par.parameter_parser(params)
    assert list(special_agent_three_par.commands_function(parsed_params, HOST_CONFIG, {})) == result
