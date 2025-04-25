#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.smtp.server_side_calls.active_check_smtp import active_check_smtp
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, IPv6Config, Secret

TEST_HOST_CONFIG = HostConfig(
    name="my_host",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)

TEST_HOST_CONFIG_IPV6 = HostConfig(
    name="my_host",
    ipv6_config=IPv6Config(address="::1"),
)

TEST_HOST_CONFIG_NO_IP = HostConfig(name="my_host", ipv4_config=None, macros={"$x": "::1"})

DAY = 86400.0


@pytest.mark.parametrize(
    "params,expected_name,expected_args",
    [
        ({"name": "foo"}, "SMTP foo", ["-4", "-H", "1.2.3.4"]),
        (
            {
                "name": "^My Name",
                "expect": "expect",
                "port": 123,
                "address_family": "ipv4",
                "commands": ["cmda", "cmdb"],
                "command_responses": ["rspa", "rspb"],
                "from_address": "home",
                "fqdn": "at.home.world",
                "cert_days": ("fixed", (42 * DAY, 23 * DAY)),
                "starttls": True,
                "auth": {"username": "me", "password": Secret(42)},
                "response_time": ("fixed", (23.0, 42.0)),
                "timeout": 110.0,
            },
            "My Name",
            [
                "-e",
                "expect",
                "-p",
                "123",
                "-C",
                "cmda",
                "-C",
                "cmdb",
                "-R",
                "rspa",
                "-R",
                "rspb",
                "-f",
                "home",
                "-w",
                "23.0000",
                "-c",
                "42.0000",
                "-t",
                "110",
                "-A",
                "LOGIN",
                "-U",
                "me",
                "-P",
                Secret(42).unsafe(),
                "-S",
                "-F",
                "at.home.world",
                "-D",
                "42,23",
                "-4",
                "-H",
                "1.2.3.4",
            ],
        ),
    ],
)
def test_check_smtp_argument_parsing(
    params: Mapping[str, object],
    expected_name: str,
    expected_args: Sequence[str | Secret],
) -> None:
    """Tests if all required arguments are present."""
    (cmd,) = active_check_smtp(params, TEST_HOST_CONFIG)
    assert cmd.service_description == expected_name
    assert cmd.command_arguments == expected_args


@pytest.mark.parametrize(
    "params,expected_name,expected_args",
    [
        (
            {"name": "foo", "hostname": "1.2.3.4", "address_family": "ipv4"},
            "SMTP foo",
            ["-4", "-H", "1.2.3.4"],
        ),
        (
            {"name": "foo", "hostname": "$x", "address_family": "ipv6"},
            "SMTP foo",
            ["-6", "-H", "::1"],
        ),
        (
            {"name": "^My Name", "hostname": "params_hostname"},
            "My Name",
            ["-4", "-H", "params_hostname"],
        ),
    ],
)
def test_check_smtp_argument_parsing_no_ip(
    params: Mapping[str, object],
    expected_name: str,
    expected_args: Sequence[str | Secret],
) -> None:
    (cmd,) = active_check_smtp(params, TEST_HOST_CONFIG_NO_IP)
    assert cmd.service_description == expected_name
    assert cmd.command_arguments == expected_args


def test_check_smtp_argument_parsing_exception() -> None:
    with pytest.raises(Exception):
        (_, _) = active_check_smtp({"name": "foo"}, TEST_HOST_CONFIG_NO_IP)


def test_mismatching_family_config_ipv6() -> None:
    params = {
        "name": "^My Name",
        "address_family": "ipv6",
    }

    with pytest.raises(ValueError, match="IPv6"):
        list(active_check_smtp(params, TEST_HOST_CONFIG))


def test_mismatching_family_config_ipv4_no_exception() -> None:
    params = {
        "name": "^My Name",
        "address_family": "ipv4",
    }

    x = list(active_check_smtp(params, TEST_HOST_CONFIG_IPV6))
    assert any(arg == "::1" for arg in x[0].command_arguments)
