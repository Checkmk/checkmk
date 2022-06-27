#!/usr/bin/env python3

# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.wato.special_agents.prometheus import _transform_agent_prometheus


@pytest.mark.parametrize(
    "parameters, expected_result",
    [
        (
            {},
            {
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": "host_name",
                "port": 9090,
            },
            {
                "connection": ("host_name", {"port": 9090}),
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": ("url_custom", {"url_address": "custom_url"}),
                "port": 9090,
            },
            {
                "connection": ("url_custom", {"url_address": "custom_url"}),
                "verify-cert": False,
            },
        ),
        (
            {
                "connection": "ip_address",
                "port": 9090,
                "auth_basic": {"username": "asdasd", "password": ("password", "asd")},
            },
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": False,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
        ),
        (
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
            {
                "connection": ("ip_address", {"port": 9090}),
                "verify-cert": True,
                "auth_basic": (
                    "auth_login",
                    {"username": "asdasd", "password": ("password", "asd")},
                ),
            },
        ),
    ],
)
def test__transform_agent_prometheus(parameters, expected_result) -> None:
    assert _transform_agent_prometheus(parameters) == expected_result
