#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.icmp import active_check_icmp
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPAddressFamily

HOST_CONFIG = HostConfig(
    name="hostname",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
    ipv4address="0.0.0.2",
    ipv6address="fe80::240",
    additional_ipv4addresses=["0.0.0.4", "0.0.0.5"],
    additional_ipv6addresses=[
        "fe80::241",
        "fe80::242",
        "fe80::243",
    ],
)


@pytest.mark.parametrize(
    "params, expected_result",
    [
        pytest.param(
            {"timeout": 30},
            [
                ActiveCheckCommand(
                    "PING", ["-t", "30", "-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.1"]
                )
            ],
            id="timeout",
        ),
        pytest.param(
            {"address": "alias"},
            [ActiveCheckCommand("PING", ["-w", "200.00,80%", "-c", "500.00,100%", "host_alias"])],
            id="alias",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1")},
            [
                ActiveCheckCommand(
                    "PING IPv4/1", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"]
                )
            ],
            id="indexed ipv4 address",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3")},
            [
                ActiveCheckCommand(
                    "PING IPv6/3", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                )
            ],
            id="indexed ipv6 address",
        ),
        pytest.param(
            {"address": "all_ipv4addresses"},
            [
                ActiveCheckCommand(
                    "PING all IPv4 Addresses",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.2", "0.0.0.4", "0.0.0.5"],
                )
            ],
            id="all ipv4 addresses",
        ),
        pytest.param(
            {"address": "all_ipv6addresses"},
            [
                ActiveCheckCommand(
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
                ActiveCheckCommand(
                    "PING", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4", "0.0.0.5"]
                )
            ],
            id="additional ipv4 addresses",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses"},
            [
                ActiveCheckCommand(
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
            [
                ActiveCheckCommand(
                    "PING", ["-w", "200.00,80%", "-c", "500.00,100%", "my.custom.address"]
                )
            ],
            id="explicit address",
        ),
        pytest.param(
            {"timeout": 30, "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING 0.0.0.1", ["-t", "30", "-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.1"]
                )
            ],
            id="timeout multiple services",
        ),
        pytest.param(
            {"address": "alias", "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING host_alias", ["-w", "200.00,80%", "-c", "500.00,100%", "host_alias"]
                )
            ],
            id="alias multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv4address", "1"), "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING 0.0.0.4", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"]
                )
            ],
            id="indexed ipv4 address multiple services",
        ),
        pytest.param(
            {"address": ("indexed_ipv6address", "3"), "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING fe80::243", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                )
            ],
            id="indexed ipv6 address multiple services",
        ),
        pytest.param(
            {"address": "all_ipv4addresses", "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING 0.0.0.2",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.2"],
                ),
                ActiveCheckCommand(
                    "PING 0.0.0.4",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"],
                ),
                ActiveCheckCommand(
                    "PING 0.0.0.5",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.5"],
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "all_ipv6addresses", "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING fe80::240",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::240"],
                ),
                ActiveCheckCommand(
                    "PING fe80::241",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::241"],
                ),
                ActiveCheckCommand(
                    "PING fe80::242",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::242"],
                ),
                ActiveCheckCommand(
                    "PING fe80::243",
                    ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"],
                ),
            ],
            id="all ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv4addresses", "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING 0.0.0.4", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.4"]
                ),
                ActiveCheckCommand(
                    "PING 0.0.0.5", ["-w", "200.00,80%", "-c", "500.00,100%", "0.0.0.5"]
                ),
            ],
            id="additional ipv4 addresses multiple services",
        ),
        pytest.param(
            {"address": "additional_ipv6addresses", "multiple_services": True},
            [
                ActiveCheckCommand(
                    "PING fe80::241", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::241"]
                ),
                ActiveCheckCommand(
                    "PING fe80::242", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::242"]
                ),
                ActiveCheckCommand(
                    "PING fe80::243", ["-w", "200.00,80%", "-c", "500.00,100%", "-6", "fe80::243"]
                ),
            ],
            id="additional ipv6 addresses multiple services",
        ),
        pytest.param(
            {"address": ("explicit", "my.custom.address"), "multiple_services": True},
            [
                ActiveCheckCommand(
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
    expected_result: Sequence[ActiveCheckCommand],
) -> None:
    services = list(
        active_check_icmp.commands_function(
            active_check_icmp.parameter_parser(params),
            HOST_CONFIG,
            {},
        )
    )
    assert services == expected_result
