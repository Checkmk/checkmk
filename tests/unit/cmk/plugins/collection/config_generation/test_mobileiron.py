#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.config_generation.v1 import (
    HostConfig,
    IPAddressFamily,
    PlainTextSecret,
    Secret,
    StoredSecret,
)
from cmk.plugins.collection.config_generation.mobileiron import special_agent_mobileiron

HOST_CONFIG = HostConfig(
    name="mobileironhostname",
    address="11.211.3.32",
    alias="host_alias",
    ip_family=IPAddressFamily.IPv4,
)


@pytest.mark.parametrize(
    ["params", "expected_args"],
    [
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("password", "mobileironpassword"),
                "proxy": (
                    "url",
                    "abc:8567",
                ),
                "partition": ["10"],
                "key-fields": ("somefield",),
                "android-regex": ["asdf", "foo", "^bar"],
                "ios-regex": [".*"],
                "other-regex": [".*"],
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                PlainTextSecret(value="mobileironpassword", format="%s"),
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
                "somefield",
            ],
            id="explicit_password",
        ),
        pytest.param(
            {
                "username": "mobileironuser",
                "password": ("store", "mobileironpassword"),
                "key-fields": ("somefield",),
                "partition": ["10", "20"],
            },
            [
                "-u",
                "mobileironuser",
                "-p",
                StoredSecret(value="mobileironpassword", format="%s"),
                "--partition",
                "10,20",
                "--hostname",
                "mobileironhostname",
                "--key-fields",
                "somefield",
            ],
            id="password_from_store",
        ),
    ],
)
def test_agent_mobileiron_arguments(
    params: Mapping[str, object],
    expected_args: Sequence[str | Secret],
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = special_agent_mobileiron.parameter_parser(params)
    commands = list(special_agent_mobileiron.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args
