#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.base.legacy_checks.agent_alertmanager import agent_alertmanager_arguments


@pytest.mark.parametrize(
    ["params", "expected_result"],
    [
        pytest.param(
            {
                "hostname": "",
                "connection": "my-server",
                "verify-cert": False,
                "protocol": "http",
                "ignore_alerts": {
                    "ignore_na": True,
                    "ignore_alert_rules": [],
                    "ignore_alert_groups": [],
                },
            },
            [
                "--config",
                "{'hostname': '', 'connection': 'my-server', 'verify-cert': False, "
                "'protocol': 'http', 'ignore_alerts': {'ignore_na': True, "
                "'ignore_alert_rules': [], 'ignore_alert_groups': []}}",
            ],
            id="without credentials",
        ),
        pytest.param(
            {
                "hostname": "my-host",
                "connection": "my-server",
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "user", "password": ("password", "password")},
                ),
                "protocol": "http",
                "ignore_alerts": {"ignore_alert_rules": ["a", "b"], "ignore_alert_groups": ["c"]},
            },
            [
                "--config",
                "{'hostname': 'my-host', 'connection': 'my-server', 'verify-cert': True, "
                "'auth_basic': ('auth_login', {'username': 'user', 'password': "
                "('password', 'password')}), 'protocol': 'http', 'ignore_alerts': "
                "{'ignore_alert_rules': ['a', 'b'], 'ignore_alert_groups': ['c']}}",
            ],
            id="with login credentials",
        ),
        pytest.param(
            {
                "hostname": "",
                "connection": "my-server",
                "verify-cert": True,
                "auth_basic": ("auth_token", {"token": ("password", "token")}),
                "protocol": "https",
                "ignore_alerts": {
                    "ignore_na": True,
                    "ignore_alert_rules": ["a", "b"],
                    "ignore_alert_groups": [],
                },
            },
            [
                "--config",
                "{'hostname': '', 'connection': 'my-server', 'verify-cert': True, "
                "'auth_basic': ('auth_token', {'token': ('password', 'token')}), "
                "'protocol': 'https', 'ignore_alerts': {'ignore_na': True, "
                "'ignore_alert_rules': ['a', 'b'], 'ignore_alert_groups': []}}",
            ],
            id="with token",
        ),
    ],
)
def test_command_creation(
    params: Mapping[str, object],
    expected_result: Sequence[object],
) -> None:
    assert agent_alertmanager_arguments(params, "host", None) == expected_result
