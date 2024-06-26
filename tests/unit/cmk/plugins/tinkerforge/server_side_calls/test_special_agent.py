#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.tinkerforge.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config


@pytest.mark.parametrize(
    "raw_params,host_config,expected_args",
    [
        (
            {},
            HostConfig(name="test", ipv4_config=IPv4Config(address="address")),
            ["--host", "address"],
        ),
        (
            {"segment_display_brightness": 5, "segment_display_uid": "8888", "port": 4223},
            HostConfig(name="test", ipv4_config=IPv4Config(address="address")),
            [
                "--host",
                "address",
                "--port",
                "4223",
                "--segment_display_uid",
                "8888",
                "--segment_display_brightness",
                "5",
            ],
        ),
    ],
)
def test_tinkerforge_argument_parsing(
    raw_params: Mapping[str, object], host_config: HostConfig, expected_args: list[str]
) -> None:
    """Tests if all required arguments are present."""
    commands = list(commands_function(Params.model_validate(raw_params), host_config))
    assert len(commands) == 1
    arguments = commands[0].command_arguments
    assert arguments == expected_args
