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
                "www.test123.de",
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
                "proxy": {"address": "163.172.86.64"},
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
                "163.172.86.64",
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
                "www.test123.com",
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
                "p.roxy",
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
                "p.roxy",
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
                "-p",
                "23",
                "[dead:beef::face]",
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
                "[dead:beef::face]",
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
                "foo.bar",
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
                "foo.bar",
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
                "virtual.host",
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
                "$_HOSTADDRESS_4$",
                "virtual.host",
            ],
        ),
    ],
)
def test_check_http_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[str],
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
