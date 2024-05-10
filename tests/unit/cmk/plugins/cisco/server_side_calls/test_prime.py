#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.cisco.server_side_calls.prime import special_agent_cisco_prime
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
            {
                "basicauth": {"username": "bla", "password": Secret(123)},
                "port": 8080,
                "no_tls": True,
                "no_cert_check": True,
                "timeout": 60,
            },
            (
                "--hostname",
                "1.2.3.4",
                "-u",
                Secret(123).unsafe("bla:%s"),
                "--port",
                "8080",
                "--no-tls",
                "--no-cert-check",
                "--timeout",
                "60",
            ),
        ),
        (
            {},
            (
                "--hostname",
                "1.2.3.4",
            ),
        ),
        (
            {
                "host": ("host_name", None),
            },
            (
                "--hostname",
                "hostname",
            ),
        ),
        (
            {
                "host": ("ip_address", None),
            },
            (
                "--hostname",
                "1.2.3.4",
            ),
        ),
        (
            {"host": ("custom", {"host": "custom"})},
            (
                "--hostname",
                "custom",
            ),
        ),
    ],
)
def test_cisco_prime_argument_parsing(
    params: Mapping[str, object],
    expected_args: Sequence[str | Secret],
) -> None:
    (command,) = special_agent_cisco_prime(
        params,
        HostConfig(
            name="hostname",
            ipv4_config=IPv4Config(address="1.2.3.4"),
        ),
    )
    assert command.command_arguments == expected_args
