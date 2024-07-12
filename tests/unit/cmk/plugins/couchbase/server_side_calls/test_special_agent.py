#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.couchbase.server_side_calls.special_agent import special_agent_couchbase
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "host_config", "expected_result"],
    [
        pytest.param(
            {},
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "1.2.3.4",
                ]
            ),
            id="empty params",
        ),
        pytest.param(
            {
                "buckets": ["bucket1", "bucket2"],
                "timeout": 20,
                "port": 8091,
                "authentication": {
                    "username": "user",
                    "password": Secret(1),
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            SpecialAgentCommand(
                command_arguments=[
                    "--buckets",
                    "bucket1",
                    "--buckets",
                    "bucket2",
                    "--timeout",
                    "20",
                    "--port",
                    "8091",
                    "--username",
                    "user",
                    "--password",
                    Secret(id=1, format="%s", pass_safely=False),
                    "1.2.3.4",
                ]
            ),
            id="all options configured",
        ),
    ],
)
def test_commands_function(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_couchbase(
            raw_params,
            host_config,
        )
    ) == [expected_result]
