#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.gui.plugins.wato.active_checks import http


@pytest.mark.parametrize(
    ["params", "transformed_params"],
    [
        pytest.param(
            {
                "name": "test.com",
                "host": {},
                "mode": ("url", {}),
            },
            {
                "name": "test.com",
                "host": {},
                "mode": ("url", {}),
            },
            id="up-to-date format minimal",
        ),
        pytest.param(
            {
                "name": "test.com",
                "host": {"address": ("direct", "test"), "address_family": "ipv6"},
                "mode": ("url", {"timeout": 10}),
            },
            {
                "name": "test.com",
                "host": {"address": ("direct", "test"), "address_family": "ipv6"},
                "mode": ("url", {"timeout": 10}),
            },
            id="up-to-date format with host address",
        ),
        pytest.param(
            {
                "name": "test.com",
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "proxy.net",
                            "port": 80,
                            "auth": ("usr", ("password", "password")),
                        },
                    ),
                    "address_family": "ipv6",
                },
                "mode": ("url", {"timeout": 10}),
            },
            {
                "name": "test.com",
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "proxy.net",
                            "port": 80,
                            "auth": ("usr", ("password", "password")),
                        },
                    ),
                    "address_family": "ipv6",
                },
                "mode": ("url", {"timeout": 10}),
            },
            id="up-to-date format with proxy",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"address": "1.2.3.4", "virthost": "virthost"},
                "mode": ("url", {}),
            },
            {
                "name": "old.com",
                "host": {"address": ("direct", "1.2.3.4"), "virthost": "virthost"},
                "mode": ("url", {}),
            },
            id="old format with address and virtual host",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"virthost": "virthost"},
                "mode": ("cert", {"cert_days": (10, 20)}),
                "disable_sni": True,
            },
            {
                "name": "old.com",
                "host": {"virthost": "virthost"},
                "mode": ("cert", {"cert_days": (10, 20)}),
                "disable_sni": True,
            },
            id="old format with virtual host only",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"port": 443},
                "proxy": {"address": "proxy", "port": 80},
                "mode": ("cert", {"cert_days": (10, 20)}),
            },
            {
                "name": "old.com",
                "host": {"address": ("proxy", {"address": "proxy", "port": 80}), "port": 443},
                "mode": ("cert", {"cert_days": (10, 20)}),
            },
            id="old format with proxy",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"address": "my-machine", "address_family": "ipv6"},
                "proxy": {"address": "proxy", "port": 80, "auth": ("user", ("password", "pwd"))},
                "mode": ("url", {"urlize": True}),
            },
            {
                "name": "old.com",
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                    "virthost": "my-machine",
                },
                "mode": ("url", {"urlize": True}),
            },
            id="old format with address and proxy",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {"address_family": "ipv6", "virthost": "virthost"},
                "proxy": {"address": "proxy", "port": 80, "auth": ("user", ("password", "pwd"))},
                "mode": ("url", {"urlize": True}),
            },
            {
                "name": "old.com",
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                },
                "mode": ("url", {"urlize": True}),
            },
            id="old format with virtual host and proxy",
        ),
        pytest.param(
            {
                "name": "old.com",
                "host": {
                    "address": "my-machine",
                    "port": 443,
                    "address_family": "ipv6",
                    "virthost": "virthost",
                },
                "proxy": {"address": "proxy", "port": 80, "auth": ("user", ("password", "pwd"))},
                "mode": ("url", {"onredirect": "follow", "urlize": True}),
            },
            {
                "host": {
                    "address": (
                        "proxy",
                        {"address": "proxy", "auth": ("user", ("password", "pwd")), "port": 80},
                    ),
                    "address_family": "ipv6",
                    "port": 443,
                    "virthost": "my-machine",
                },
                "mode": ("url", {"onredirect": "follow", "urlize": True}),
                "name": "old.com",
            },
            id="old format with address, virtual host and proxy",
        ),
    ],
)
def test_migrate(
    params: Mapping[str, Any],
    transformed_params: Mapping[str, Any],
) -> None:
    assert http._migrate(params) == transformed_params
