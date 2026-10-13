#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.ldapcheck.server_side_calls.active_check_ldap import active_check_ldap
from cmk.server_side_calls.v1 import ActiveCheckCommand, HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="ipaddress"),
)

MINIMAL_PARAMS = {
    "name": "foo",
    "base_dn": "bar",
}


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
            {
                **MINIMAL_PARAMS,
                "hostname": "baz",
            },
            ["-H", "baz", "-b", "bar"],
        ),
        (
            {
                **MINIMAL_PARAMS,
                "hostname": "baz",
                "port": 389,
                "version": "v2",
            },
            ["-H", "baz", "-b", "bar", "-p", "389", "-2"],
        ),
    ],
)
def test_check_ldap_argument_parsing(
    params: Mapping[str, str | float], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    (command,) = active_check_ldap(params, HOST_CONFIG)
    assert command.command_arguments == expected_args


def test_check_ldap_authentication() -> None:
    assert list(
        active_check_ldap(
            {
                **MINIMAL_PARAMS,
                "authentication": {
                    "bind_dn": "baz",
                    "password": Secret(0),
                },
            },
            HOST_CONFIG,
        )
    ) == [
        ActiveCheckCommand(
            service_description="LDAP foo",
            command_arguments=[
                "-H",
                "ipaddress",
                "-b",
                "bar",
                "-D",
                "baz",
                "-P",
                Secret(0).unsafe(),
            ],
        )
    ]


def test_check_ldap_response_time() -> None:
    assert list(
        active_check_ldap(
            {
                **MINIMAL_PARAMS,
                "response_time": ("fixed", (1.2, 2.3)),
            },
            HOST_CONFIG,
        )
    ) == [
        ActiveCheckCommand(
            service_description="LDAP foo",
            command_arguments=[
                "-H",
                "ipaddress",
                "-b",
                "bar",
                "-w",
                "1.2",
                "-c",
                "2.3",
            ],
        )
    ]
