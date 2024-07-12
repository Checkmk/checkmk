#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.smb.server_side_calls.disk_smb import active_check_config
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="0.0.0.1"),
)


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "share": "foo",
                "levels": ("fixed", (85.0, 95.0)),
                "host": ("use_parent_host", ""),
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
                "levels": ("no_levels", None),
                "host": ("define_host", "test_host"),
                "auth": {"user": "user_1", "password": Secret(1)},
                "ip_address": "100.100.10.1",
            },
            [
                "foo",
                "-H",
                "test_host",
                "-u",
                "user_1",
                "--password-reference",
                Secret(1),
                "-a",
                "100.100.10.1",
            ],
        ),
        (
            {
                "share": "foo",
                "levels": ("fixed", (85.0, 95.0)),
                "host": ("define_host", "host_str"),
                "port": 123,
                "workgroup": "_workgroup",
                "auth": {"user": "user_1", "password": Secret(1)},
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
                "--port",
                "123",
                "-u",
                "user_1",
                "--password-reference",
                Secret(1),
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
    commands = list(active_check_config(params, HOST_CONFIG))
    assert commands[0].command_arguments == expected_args
