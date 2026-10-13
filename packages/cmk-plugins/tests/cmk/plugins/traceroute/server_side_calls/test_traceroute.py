#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.traceroute.server_side_calls.traceroute import active_check_traceroute
from cmk.server_side_calls.v1 import HostConfig, IPv4Config


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "dns": True,
                "routers": [("127.0.0.1", "W")],
                "method": "icmp",
                "address_family": "ipv4",
            },
            [
                "ipaddress",
                "--use_dns",
                "--probe_method=icmp",
                "--ip_address_family=ipv4",
                "--routers_missing_warn",
                "127.0.0.1",
                "--routers_missing_crit",
                "--routers_found_warn",
                "--routers_found_crit",
            ],
        ),
        (
            {
                "dns": False,
                "routers": [
                    ("router1", "W"),
                    ("router2", "C"),
                    ("1.2.3.4", "c"),
                    ("1.2.3.5", "w"),
                ],
                "method": None,
                "address_family": "ipv4",
            },
            [
                "ipaddress",
                "--probe_method=udp",
                "--ip_address_family=ipv4",
                "--routers_missing_warn",
                "router1",
                "--routers_missing_crit",
                "router2",
                "--routers_found_warn",
                "1.2.3.5",
                "--routers_found_crit",
                "1.2.3.4",
            ],
        ),
        (
            {
                "dns": True,
                "routers": [
                    ("router1", "W"),
                    ("192.168.1.1", "W"),
                ],
                "method": None,
                "address_family": "ipv6",
            },
            [
                "ipaddress",
                "--use_dns",
                "--probe_method=udp",
                "--ip_address_family=ipv6",
                "--routers_missing_warn",
                "router1",
                "192.168.1.1",
                "--routers_missing_crit",
                "--routers_found_warn",
                "--routers_found_crit",
            ],
        ),
    ],
)
def test_check_traceroute_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    (command,) = active_check_traceroute(
        params,
        HostConfig(
            name="hostname",
            ipv4_config=IPv4Config(address="ipaddress"),
        ),
    )
    assert command.command_arguments == expected_args
