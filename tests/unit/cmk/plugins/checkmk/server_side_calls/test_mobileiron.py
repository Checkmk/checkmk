#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.mobileiron.server_side_calls.mobileiron import special_agent_mobileiron
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, URLProxy

HOST_CONFIG = HostConfig(
    name="mobileironhostname",
    ipv4_config=IPv4Config(address="11.211.3.32"),
)


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "username": "mobileironuser",
                "password": Secret(23),
                "proxy": URLProxy(url="abc:8567"),
                "partition": ["10"],
                "key_fields": "deviceModel_serialNumber",
                "android_regex": ["asdf", "foo", "^bar"],
                "ios_regex": [".*"],
                "other_regex": [".*"],
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                Secret(23).unsafe(),
                "--partition",
                "10",
                "--hostname",
                "mobileironhostname",
                "--proxy",
                "abc:8567",
                "--android-regex=asdf",
                "--android-regex=foo",
                "--android-regex=^bar",
                "--ios-regex=.*",
                "--other-regex=.*",
                "--key-fields",
                "deviceModel",
                "--key-fields",
                "serialNumber",
            ],
            id="explicit_password",
        ),
    ],
)
def test_agent_mobileiron_arguments(
    params: Mapping[str, object],
    expected_args: Sequence[str | Secret],
) -> None:
    """Tests if all required arguments are present."""
    commands = list(special_agent_mobileiron(params, HOST_CONFIG))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
