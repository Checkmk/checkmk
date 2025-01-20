#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.plugins.alertmanager.server_side_calls.special_agent import special_agent_alertmanager
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, Secret, SpecialAgentCommand


@pytest.mark.parametrize(
    ["raw_params", "expected_result"],
    [
        pytest.param(
            {
                "hostname": "",
                "connection": "my-server",
                "verify_cert": True,
                "protocol": "http",
                "ignore_alerts": {
                    "ignore_na": True,
                    "ignore_alert_rules": [],
                    "ignore_alert_groups": [],
                },
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--config",
                    "{'hostname': '', 'connection': 'my-server', "
                    "'protocol': 'http', 'ignore_alerts': "
                    "{'ignore_na': True, 'ignore_alert_rules': [], "
                    "'ignore_alert_groups': []}}",
                ]
            ),
            id="without credentials",
        ),
        pytest.param(
            {
                "hostname": "my-host",
                "connection": "my-server",
                "verify_cert": False,
                "auth_basic": (
                    "auth_login",
                    {"username": "user", "password": Secret(0)},
                ),
                "protocol": "http",
                "ignore_alerts": {
                    "ignore_na": False,
                    "ignore_alert_rules": ["a", "b"],
                    "ignore_alert_groups": ["c"],
                },
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--config",
                    "{'hostname': 'my-host', 'connection': "
                    "'my-server', 'protocol': 'http', "
                    "'ignore_alerts': {'ignore_na': False, "
                    "'ignore_alert_rules': ['a', 'b'], "
                    "'ignore_alert_groups': ['c']}}",
                    "--disable-cert-verification",
                    "auth_login",
                    "--username",
                    "user",
                    "--password-reference",
                    Secret(0),
                ]
            ),
            id="with login credentials",
        ),
        pytest.param(
            {
                "hostname": "",
                "connection": "my-server",
                "verify_cert": False,
                "auth_basic": ("auth_token", {"token": Secret(0)}),
                "protocol": "https",
                "ignore_alerts": {
                    "ignore_na": True,
                    "ignore_alert_rules": ["a", "b"],
                    "ignore_alert_groups": [],
                },
            },
            SpecialAgentCommand(
                command_arguments=[
                    "--config",
                    "{'hostname': '', 'connection': 'my-server', "
                    "'protocol': 'https', 'ignore_alerts': "
                    "{'ignore_na': True, 'ignore_alert_rules': ['a', "
                    "'b'], 'ignore_alert_groups': []}}",
                    "--disable-cert-verification",
                    "auth_token",
                    "--token",
                    Secret(0),
                ]
            ),
            id="with token",
        ),
    ],
)
def test_command_creation(
    raw_params: Mapping[str, object],
    expected_result: SpecialAgentCommand,
) -> None:
    assert list(
        special_agent_alertmanager(
            raw_params,
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
        )
    ) == [expected_result]
