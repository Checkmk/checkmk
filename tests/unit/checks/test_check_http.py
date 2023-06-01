#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.testlib import ActiveCheck


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            {
                "name": "irrelevant",
                "mode": (
                    "url",
                    {
                        "onredirect": "follow",
                        "uri": "/images",
                        "urlize": True,
                    },
                ),
                "host": {
                    "virthost": "www.test123.de",
                    "address": ("direct", "www.test123.de"),
                    "port": 80,
                },
            },
            [
                "-u",
                "/images",
                "--onredirect=follow",
                "-L",
                "--sni",
                "-p",
                "80",
                "-I",
                "www.test123.de",
                "-H",
                "www.test123.de",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": (
                    "url",
                    {
                        "extended_perfdata": True,
                        "method": "CONNECT",
                        "ssl": "auto",
                        "uri": "/images",
                    },
                ),
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "163.172.86.64",
                            "auth": (
                                "user",
                                ("password", "pwd"),
                            ),
                        },
                    ),
                    "port": 3128,
                    "virthost": "www.test123.de",
                },
            },
            [
                "-u",
                "/images",
                "--ssl",
                "--extended-perfdata",
                "-j",
                "CONNECT",
                "--sni",
                "-b",
                "user:pwd",
                "-I",
                "163.172.86.64",
                "-H",
                "www.test123.de:3128",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": (
                    "cert",
                    {"cert_days": (10, 20)},
                ),
                "host": {
                    "address": ("direct", "www.test123.com"),
                    "port": 42,
                },
            },
            [
                "-C",
                "10,20",
                "--sni",
                "-p",
                "42",
                "-I",
                "www.test123.com",
                "-H",
                "www.test123.com",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("cert", {"cert_days": (10, 20)}),
                "host": {
                    "address": ("proxy", {"address": "p.roxy"}),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "--sni",
                "-I",
                "p.roxy",
                "-H",
                "www.test123.com:42",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": (
                    "cert",
                    {"cert_days": (10, 20)},
                ),
                "host": {
                    "address": ("proxy", {"address": "p.roxy"}),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "--sni",
                "-I",
                "p.roxy",
                "-H",
                "www.test123.com:42",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": (
                    "cert",
                    {"cert_days": (10, 20)},
                ),
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "[dead:beef::face]",
                            "port": 23,
                            "auth": (
                                "user",
                                ("store", "check_http"),
                            ),
                        },
                    ),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "--sni",
                "-b",
                ("store", "check_http", "user:%s"),
                "-p",
                "23",
                "-I",
                "[dead:beef::face]",
                "-H",
                "www.test123.com:42",
            ],
        ),
        (
            {
                "host": {
                    "address": ("proxy", {"address": "[dead:beef::face]", "port": 23}),
                    "port": 42,
                    "address_family": "ipv6",
                    "virthost": "www.test123.com",
                },
                "mode": ("cert", {"cert_days": (10, 20)}),
                "disable_sni": True,
            },
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "-6",
                "-p",
                "23",
                "-I",
                "[dead:beef::face]",
                "-H",
                "www.test123.com:42",
            ],
        ),
        (
            {
                "host": {"address": ("direct", "www.test123.com")},
                "mode": ("url", {"ssl": "auto"}),
            },
            [
                "--ssl",
                "--sni",
                "-I",
                "www.test123.com",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": (
                    "url",
                    {"method": "PUT"},
                ),
                "host": {
                    "address": ("proxy", {"address": "foo.bar"}),
                    "virthost": "virtual.host",
                },
            },
            [
                "-j",
                "PUT",
                "--sni",
                "-I",
                "foo.bar",
                "-H",
                "virtual.host",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {
                    "address": ("proxy", {"address": "foo.bar"}),
                    "virthost": "virtual.host",
                },
            },
            [
                "-j",
                "CONNECT",
                "--sni",
                "-I",
                "foo.bar",
                "-H",
                "virtual.host",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {"virthost": "virtual.host", "address": ("direct", "virtual.host")},
            },
            [
                "--sni",
                "-I",
                "virtual.host",
                "-H",
                "virtual.host",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {"virthost": "virtual.host"},
            },
            [
                "--sni",
                "-I",
                "$_HOSTADDRESS_4$",
                "-H",
                "virtual.host",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {"address_family": None},
            },
            [
                "--sni",
                "-I",
                "$_HOSTADDRESS_4$",
            ],
        ),
        pytest.param(
            {
                "name": "irrelevant",
                "host": {
                    "address": ("proxy", {"address": "proxy", "port": 123}),
                    "port": 43,
                    "address_family": "ipv6",
                },
                "mode": ("url", {}),
            },
            [
                "-j",
                "CONNECT",
                "-6",
                "--sni",
                "-p",
                "123",
                "-I",
                "proxy",
                "-H",
                "$_HOSTADDRESS_6$:43",
            ],
            id="proxy + virtual host (which is ignored)",
        ),
    ],
)
def test_check_http_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[object],
) -> None:
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_http")
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize(
    "params,expected_description",
    [
        (
            {
                "name": "No SSL Test",
                "host": {},
                "mode": (
                    "url",
                    {},
                ),
            },
            "HTTP No SSL Test",
        ),
        (
            {
                "name": "Test with SSL",
                "host": {},
                "mode": (
                    "url",
                    {"ssl": "auto"},
                ),
            },
            "HTTPS Test with SSL",
        ),
        (
            {
                "name": "^No Prefix Test",
                "host": {},
                "mode": (
                    "url",
                    {"ssl": "auto"},
                ),
            },
            "No Prefix Test",
        ),
    ],
)
def test_check_http_service_description(
    params: Mapping[str, Any],
    expected_description: str,
) -> None:
    active_check = ActiveCheck("check_http")
    assert active_check.run_service_description(params) == expected_description
