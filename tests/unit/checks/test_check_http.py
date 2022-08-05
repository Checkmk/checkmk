#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence

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
                    "address": "www.test123.de",
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
                "proxy": {
                    "address": "163.172.86.64",
                    "auth": (
                        "user",
                        ("password", "pwd"),
                    ),
                },
                "host": {
                    "virthost": "www.test123.de",
                    "address": "www.test123.de",
                    "port": 3128,
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
                    "address": "www.test123.com",
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
                "proxy": {"address": "p.roxy"},
                "host": {
                    "address": "www.test123.com",
                    "port": 42,
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
                "proxy": {"address": "p.roxy"},
                "host": {
                    "address": "www.test123.com",
                    "port": 42,
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
                "proxy": {
                    "address": "[dead:beef::face]",
                    "port": 23,
                    "auth": (
                        "user",
                        ("store", "check_http"),
                    ),
                },
                "host": {
                    "address": "www.test123.com",
                    "port": 42,
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
                "host": {"address": "www.test123.com", "port": 42, "address_family": "ipv6"},
                "proxy": {"address": "[dead:beef::face]", "port": 23},
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
                "host": {
                    "address": "www.test123.com",
                },
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
                    {},
                ),
                "proxy": {"address": "foo.bar"},
                "host": {
                    "virthost": "virtual.host",
                    "address": "virtual.host",
                },
            },
            [
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
                "proxy": {"address": "foo.bar"},
                "host": {
                    "virthost": "virtual.host",
                    "address": "virtual.host",
                },
            },
            [
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
                    "virthost": "virtual.host",
                    "address": "virtual.host",
                },
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
        pytest.param(
            {
                "name": "irrelevant",
                "host": {"virthost": "virtual.host", "port": 43, "address_family": "ipv6"},
                "proxy": {"address": "proxy", "port": 123},
                "mode": ("url", {}),
            },
            [
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
