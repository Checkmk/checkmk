#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.graylog.server_side_calls.special_agent import commands_function, Params
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, SpecialAgentCommand
from cmk.server_side_calls.v1._utils import Secret


@pytest.mark.parametrize(
    "raw_params, host_config, expected_args",
    [
        pytest.param(
            {
                "user": "user",
                "password": Secret(id=1, pass_safely=True),
                "instance": "test",
                "protocol": "https",
                "sections": ["alerts"],
                "since": 1800,
                "display_node_details": "host",
                "display_sidecar_details": "host",
                "display_source_details": "host",
                "alerts_since": 1200,
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "--proto",
                    "https",
                    "--sections",
                    "alerts",
                    "--since",
                    "1800",
                    "--user",
                    "user",
                    "--password",
                    Secret(id=1, format="%s", pass_safely=False),
                    "--display_node_details",
                    "host",
                    "--display_sidecar_details",
                    "host",
                    "--display_source_details",
                    "host",
                    "--alerts_since",
                    "1200",
                    "test",
                ],
                stdin=None,
            ),
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
