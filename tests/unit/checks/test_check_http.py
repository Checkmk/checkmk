#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import ActiveCheck

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "params,expected_args",
    [
        (
            (
                None,
                {
                    "onredirect": "follow",
                    "port": 80,
                    "uri": "/images",
                    "urlize": True,
                    "virthost": ("www.test123.de", True),
                },
            ),
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
            (
                None,
                {
                    "extended_perfdata": True,
                    "method": "CONNECT",
                    "port": 3128,
                    "proxy": "163.172.86.64",
                    "ssl": "auto",
                    "uri": "/images",
                    "virthost": ("www.test123.de", True),
                },
            ),
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
            (
                None,
                {
                    "cert_days": (10, 20),
                    "cert_host": "www.test123.com",
                    "port": "42",
                },
            ),
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
            (
                None,
                {
                    "cert_days": (10, 20),
                    "cert_host": "www.test123.com",
                    "port": "42",
                    "proxy": "p.roxy",
                },
            ),
            ["-C", "10,20", "--ssl", "-j", "CONNECT", "--sni", "p.roxy", "www.test123.com:42"],
        ),
        (
            (
                None,
                {
                    "cert_days": (10, 20),
                    "cert_host": "www.test123.com",
                    "port": "42",
                    "proxy": "p.roxy:23",
                },
            ),
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "--sni",
                "-p",
                "23",
                "p.roxy",
                "www.test123.com:42",
            ],
        ),
        (
            (
                None,
                {
                    "cert_days": (10, 20),
                    "cert_host": "www.test123.com",
                    "port": "42",
                    "proxy": "[dead:beef::face]:23",
                },
            ),
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
            ["--ssl", "--sni", "www.test123.com"],
        ),
        (
            (
                None,
                {
                    "virthost": ("virtual.host", True),
                    "proxy": "foo.bar",
                },
            ),
            ["--sni", "foo.bar", "virtual.host"],
        ),
        (
            (
                None,
                {
                    "virthost": ("virtual.host", False),
                    "proxy": "foo.bar",
                },
            ),
            ["--sni", "foo.bar", "virtual.host"],
        ),
        (
            (
                None,
                {
                    "virthost": ("virtual.host", True),
                },
            ),
            ["--sni", "virtual.host", "virtual.host"],
        ),
        (
            (
                None,
                {
                    "virthost": ("virtual.host", False),
                },
            ),
            ["--sni", "$_HOSTADDRESS_4$", "virtual.host"],
        ),
    ],
)
def test_check_http_argument_parsing(params, expected_args):
    """Tests if all required arguments are present."""
    active_check = ActiveCheck("check_http")
    assert active_check.run_argument_function(params) == expected_args


@pytest.mark.parametrize(
    "params,expected_description",
    [
        (
            ("No SSL Test", {}),
            "HTTP No SSL Test",
        ),
        (
            ("Test with SSL", {"ssl": "auto"}),
            "HTTPS Test with SSL",
        ),
        (
            ("^No Prefix Test", {}),
            "No Prefix Test",
        ),
    ],
)
def test_check_http_service_description(params, expected_description):
    active_check = ActiveCheck("check_http")
    assert active_check.run_service_description(params) == expected_description
