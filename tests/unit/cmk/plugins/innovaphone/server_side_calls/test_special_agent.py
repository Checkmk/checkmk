#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.innovaphone.server_side_calls.special_agent import special_agent_innovaphone
from cmk.server_side_calls.v1 import HostConfig, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "host_config", "expected_result"],
    [
        pytest.param(
            {
                "cert_verification": True,
                "auth_basic": {
                    "username": "user",
                    "password": Secret(1),
                },
            },
            HostConfig(name="hostname"),
            SpecialAgentCommand(
                command_arguments=[
                    "hostname",
                    "user",
                    Secret(id=1, format="%s", pass_safely=False),
                ]
            ),
            id="certification verification enabled, without protocol",
        ),
        pytest.param(
            {
                "protocol": "https",
                "cert_verification": False,
                "auth_basic": {
                    "username": "user",
                    "password": Secret(1),
                },
            },
            HostConfig(name="hostname"),
            SpecialAgentCommand(
                command_arguments=[
                    "hostname",
                    "user",
                    Secret(id=1, format="%s", pass_safely=False),
                    "--protocol",
                    "https",
                    "--no-cert-check",
                ]
            ),
            id="certification verification disabled, with protocol",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    host_config: HostConfig,
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_innovaphone(
            raw_params,
            host_config,
        )
    ) == [expected_result]
