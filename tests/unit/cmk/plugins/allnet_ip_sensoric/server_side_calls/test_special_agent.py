#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.allnet_ip_sensoric.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand


@pytest.mark.parametrize(
    "raw_params, host_config, expected_args",
    [
        pytest.param(
            {},
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(command_arguments=["1.2.3.4"], stdin=None),
            id="no_params",
        ),
        pytest.param(
            {"timeout": 20.0},
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(command_arguments=["--timeout", "20", "1.2.3.4"], stdin=None),
            id="with_params",
        ),
    ],
)
def test_commands_function(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_args: SpecialAgentCommand,
) -> None:
    assert list(
        commands_function(
            Params.model_validate(raw_params),
            host_config,
        )
    ) == [expected_args]
