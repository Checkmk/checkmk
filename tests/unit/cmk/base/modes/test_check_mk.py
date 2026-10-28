#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket

import pytest

from cmk.base.modes.check_mk import fake_dns_address, mandatory_ip_lookup, state_exit_code
from cmk.ccc.exceptions import MKBailOut
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.utils import ip_lookup


def test_no_fake_dns_option_leaves_the_lookup_alone() -> None:
    assert fake_dns_address({}) is None


def test_the_fake_dns_option_is_a_host_address() -> None:
    assert fake_dns_address({"fake-dns": "1.2.3.4"}) == HostAddress("1.2.3.4")


def test_an_invalid_fake_dns_address_is_refused() -> None:
    with pytest.raises(MKBailOut):
        fake_dns_address({"fake-dns": "not an address!"})


@pytest.mark.parametrize(
    ["state", "expected"],
    [
        (0, CLIExitCode.SUCCESS),
        (1, CLIExitCode.FAILURE),
        (2, CLIExitCode.ERROR),
        (3, CLIExitCode.UNKNOWN),
        (4, CLIExitCode.UNKNOWN),
        (-1, CLIExitCode.UNKNOWN),
        (127, CLIExitCode.UNKNOWN),
    ],
)
def test_a_state_exits_with_its_monitoring_meaning(state: int, expected: CLIExitCode) -> None:
    assert state_exit_code(state) == expected


def _ip_lookup_config() -> ip_lookup.IPLookupConfig:
    return ip_lookup.IPLookupConfig(
        debug=False,
        ip_stack_config=lambda host_name: ip_lookup.IPStackConfig.IPv4,  # noqa: ARG005
        is_snmp_host=lambda host_name: False,  # noqa: ARG005
        is_snmp_management=lambda host_name: False,  # noqa: ARG005
        is_use_walk_host=lambda host_name: False,  # noqa: ARG005
        default_address_family=lambda host_name: socket.AddressFamily.AF_INET,  # noqa: ARG005
        management_address=lambda host_name, family: None,  # noqa: ARG005
        is_dyndns_host=lambda host_name: False,  # noqa: ARG005
        ipv4_addresses={HostName("testhost"): HostAddress("10.0.0.1")},
        ipv6_addresses={},
        simulation_mode=False,
        fake_dns=None,
        use_dns_cache=False,
    )


def test_without_usewalk_the_address_is_mandatory() -> None:
    lookup = mandatory_ip_lookup({}, _ip_lookup_config())

    assert lookup is not None and lookup(
        HostName("testhost"), socket.AddressFamily.AF_INET
    ) == HostAddress("10.0.0.1")


def test_usewalk_does_not_insist_on_an_address() -> None:
    assert mandatory_ip_lookup({"usewalk": True}, _ip_lookup_config()) is None
