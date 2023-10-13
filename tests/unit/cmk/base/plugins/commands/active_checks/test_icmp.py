#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from ipaddress import IPv4Address, IPv6Address

import pytest

from tests.testlib import ActiveCheck

from tests.unit.conftest import FixRegister

from cmk.config_generation.v1 import ActiveService, HostConfig, IPAddressFamily

HOST_CONFIG = HostConfig(
    name="hostname",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
    ipv4address=IPv4Address("0.0.0.2"),
    ipv6address=IPv6Address("FE80::240"),
    additional_ipv4addresses=[IPv4Address("0.0.0.4"), IPv4Address("0.0.0.5")],
    additional_ipv6addresses=[
        IPv6Address("fe80::241"),
        IPv6Address("fe80::242"),
        IPv6Address("fe80::243"),
    ],
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"timeout": 30},
            [
                ActiveService(
                    "PING", ["-t", "30", "-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.1"]
                )
            ],
            id="timeout",
        ),
        pytest.param(
            {"address": "alias"},
            [ActiveService("PING", ["-w", "200.00,80%", "-c", "500.00,100%", "host_alias"])],
            id="alias",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1")},
            [ActiveService("PING IPv4/1", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"])],
            id="indexed ipv4 address",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3")},
            [
                ActiveService(
                    "PING IPv6/3", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                )
            ],
            id="indexed ipv6 address",
        ),
        pytest.param(
            {"address": "all_ipv4addresses"},
            [
                ActiveService(
                    "PING all IPv4 Addresses",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.2", "0.0.0.4", "0.0.0.5"],
                )
            ],
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "all_ipv6addresses"},
            [
                ActiveService(
                    "PING all IPv6 Addresses",
                    [
                        "-w",
                        "200.00,80%",
                        "-c",
                        "500.00,100%",
                        "-6",
                        "fe80::240",
                        "fe80::241",
                        "fe80::242",
                        "fe80::243",
                    ],
                )
            ],
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv4addresses"},
            [
                ActiveService(
                    "PING", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4", "0.0.0.5"]
                )
            ],
            id="additional ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses"},
            [
                ActiveService(
                    "PING",
                    [
                        "-w",
                        "200.00,80%",
                        "-c",
                        "500.00,100%",
                        "-6",
                        "fe80::241",
                        "fe80::242",
                        "fe80::243",
                    ],
                )
            ],
            id="additional ipv6 addresses",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address")},
            [ActiveService("PING", ["-w", "200.00,80%", "-c", "500.00,100%", "my.custom.address"])],
            id="explicit address",
        ),
        pytest.param(
            {"timeout": 30, "multiple_services": True},
            [
                ActiveService(
                    "PING 0.0.0.1", ["-t", "30", "-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.1"]
                )
            ],
            id="timeout multiple services",
        ),
        pytest.param(
            {"address": "alias", "multiple_services": True},
            [
                ActiveService(
                    "PING host_alias", ["-w", "200.00,80%", "-c", "500.00,100%", "host_alias"]
                )
            ],
            id="alias multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1"), "multiple_services": True},
            [ActiveService("PING 0.0.0.4", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"])],
            id="indexed ipv4 address multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3"), "multiple_services": True},
            [
                ActiveService(
                    "PING fe80::243", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                )
            ],
            id="indexed ipv6 address multiple services",
        ),
        pytest.param(
            {"address": "all_ipv4addresses", "multiple_services": True},
            [
                ActiveService(
                    "PING 0.0.0.2",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.2"],
                ),
                ActiveService(
                    "PING 0.0.0.4",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"],
                ),
                ActiveService(
                    "PING 0.0.0.5",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.5"],
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "all_ipv6addresses", "multiple_services": True},
            [
                ActiveService(
                    "PING fe80::240",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::240"],
                ),
                ActiveService(
                    "PING fe80::241",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::241"],
                ),
                ActiveService(
                    "PING fe80::242",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::242"],
                ),
                ActiveService(
                    "PING fe80::243",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"],
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv4addresses", "multiple_services": True},
            [
                ActiveService("PING 0.0.0.4", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"]),
                ActiveService("PING 0.0.0.5", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.5"]),
            ],
            id="additional ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses", "multiple_services": True},
            [
                ActiveService(
                    "PING fe80::241", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::241"]
                ),
                ActiveService(
                    "PING fe80::242", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::242"]
                ),
                ActiveService(
                    "PING fe80::243", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                ),
            ],
            id="additional ipv6 addresses multiple services",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address"), "multiple_services": True},
            [
                ActiveService(
                    "PING my.custom.address",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "my.custom.address"],
                )
            ],
            id="explicit address multiple services",
        ),
    ],
)
def test_generate_icmp_services(
    params: Mapping[str, object],
    expected_result: Sequence[ActiveService],
    fix_register: FixRegister,
) -> None:
    active_check = ActiveCheck("icmp")
    services = list(active_check.run_service_function(HOST_CONFIG, {}, params))
    assert services == expected_result
