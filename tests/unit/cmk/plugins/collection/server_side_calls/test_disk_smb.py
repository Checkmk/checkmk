#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.collection.server_side_calls.disk_smb import active_check_config
from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, PlainTextSecret, StoredSecret

pytestmark = pytest.mark.checks

HOST_CONFIG = HostConfig(
    name="hostname",
    address="0.0.0.1",
    alias="host_alias",
    ip_family=IPAddressFamily.IPV4,
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "share": "foo",
                "levels": (85.0, 95.0),
                "host": "use_parent_host",
            },
            [
                "foo",
                "-H",
                "0.0.0.1",
                "--levels",
                "85.0",
                "95.0",
            ],
        ),
        (
            {
                "share": "foo",
                "levels": (85.0, 95.0),
                "host": ("define_host", "test_host"),
                "auth": ("user_1", ("store", "password_id_1")),
                "ip_address": "100.100.10.1",
            },
            [
                "foo",
                "-H",
                "test_host",
                "--levels",
                "85.0",
                "95.0",
                "-u",
                "user_1",
                "-p",
                StoredSecret(value="password_id_1", format="%s"),
                "-a",
                "100.100.10.1",
            ],
        ),
        (
            {
                "share": "foo",
                "levels": (85.0, 95.0),
                "host": ("define_host", "host_str"),
                "port": 123,
                "workgroup": "_workgroup",
                "auth": ("user_1", ("password", "shhhhh")),
                "ip_address": "168.1.4.23",
            },
            [
                "foo",
                "-H",
                "host_str",
                "--levels",
                "85.0",
                "95.0",
                "-W",
                "_workgroup",
                "-P",
                "123",
                "-u",
                "user_1",
                "-p",
                PlainTextSecret(value="shhhhh", format="%s"),
                "-a",
                "168.1.4.23",
            ],
        ),
    ],
)
def test_check_disk_smb_argument_parsing(
    params: Mapping[str, object], expected_args: Sequence[str]
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = active_check_config.parameter_parser(params)
    commands = list(active_check_config.commands_function(parsed_params, HOST_CONFIG, {}))
    assert commands[0].command_arguments == expected_args
