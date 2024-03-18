#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.ldap import active_check_ldap
from cmk.server_side_calls.v1 import HostConfig, IPv4Config


@pytest.mark.parametrize(
    "params, expected_args",
    [
        (
            {
                "name": "foo",
                "base_dn": "bar",
                "hostname": "baz",
            },
            ["-H", "baz", "-b", "bar"],
        ),
        (
            {
                "name": "foo",
                "base_dn": "bar",
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
    (command,) = active_check_ldap(
        params,
        HostConfig(
            name="hostname",
            ipv4_config=IPv4Config(address="ipaddress"),
        ),
        {},
    )
    assert command.command_arguments == expected_args
