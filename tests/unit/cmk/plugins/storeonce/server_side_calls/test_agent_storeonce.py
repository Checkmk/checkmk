#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.storeonce.server_side_calls.special_agent import special_agent_storeonce
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand

HOST_CONFIG = HostConfig(
    name="hostname",
    ipv4_config=IPv4Config(address="1.2.3.4"),
)


@pytest.mark.parametrize(
    ["raw_params", "expected_args"],
    [
        pytest.param(
            {
                "password": Secret(23),
                "user": "username",
                "ignore_tls": False,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--address=hostname",
                    "--user=username",
                    f"--password={Secret(23).unsafe()}",
                ]
            ),
            id="with explicit password",
        ),
        pytest.param(
            {
                "password": Secret(id=1, pass_safely=True),
                "user": "username",
                "ignore_tls": False,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--address=hostname",
                    "--user=username",
                    "--password=Secret(id=1, format='%s', pass_safely=False)",
                ]
            ),
            id="with password from store",
        ),
    ],
)
def test_storeonce_argument_parsing_password(
    raw_params: Mapping[str, object],
    expected_args: SpecialAgentCommand,
) -> None:
    assert list(special_agent_storeonce(raw_params, HOST_CONFIG)) == [expected_args]


@pytest.mark.parametrize(
    ["raw_params", "expected_args"],
    [
        pytest.param(
            {
                "password": Secret(id=1, pass_safely=True),
                "user": "username",
                "ignore_tls": True,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--address=hostname",
                    "--user=username",
                    "--password=Secret(id=1, format='%s', pass_safely=False)",
                    "--no-cert-check",
                ]
            ),
            id="Ignore TLS certificate",
        ),
        pytest.param(
            {
                "password": Secret(id=1, pass_safely=True),
                "user": "username",
                "ignore_tls": False,
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--address=hostname",
                    "--user=username",
                    "--password=Secret(id=1, format='%s', pass_safely=False)",
                ]
            ),
            id="Do not ignore TLS certificate",
        ),
    ],
)
def test_storeonce_argument_parsing_cert_verification(
    raw_params: Mapping[str, object],
    expected_args: SpecialAgentCommand,
) -> None:
    assert list(special_agent_storeonce(raw_params, HOST_CONFIG)) == [expected_args]
