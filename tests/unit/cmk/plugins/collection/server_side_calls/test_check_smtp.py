#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.check_smtp import active_check_smtp
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, Secret, StoredSecret

TEST_HOST_CONFIG = HostConfig(
    "my_host", "1.2.3.4", "my_alias", IPAddressFamily.IPV4, ipv4address="my.ipv4.address"
)


@pytest.mark.parametrize(
    "params,expected_name,expected_args",
    [
        ({"name": "foo"}, "SMTP foo", ["-4", "-H", "my.ipv4.address"]),
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
                "cert_days": (42, 23),
                "starttls": True,
                "auth": ("me", ("store", "my_stored_secret")),
                "response_time": (23.0, 42.0),
                "timeout": 110,
            },
            "My Name",
            [
                "-e",
                "expect",
                "-p",
                "123",
                "-4",
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
                StoredSecret(value="my_stored_secret", format="%s"),
                "-S",
                "-F",
                "at.home.world",
                "-D",
                "42,23",
                "-H",
                "my.ipv4.address",
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
    (cmd,) = active_check_smtp.commands_function(
        active_check_smtp.parameter_parser(params), TEST_HOST_CONFIG, {}
    )
    assert cmd.service_description == expected_name
    assert cmd.command_arguments == expected_args
