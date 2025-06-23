#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.server_side_calls.httpv1 import (
    active_check_http,
    check_http_description,
    HttpParams,
)
from cmk.server_side_calls.v1 import HostConfig, IPv4Config, IPv6Config, Secret


@pytest.mark.parametrize(
    "params,host_config,expected_args",
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
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
                            "auth": {
                                "user": "user",
                                "password": Secret(1),
                            },
                        },
                    ),
                    "port": 3128,
                    "virthost": "www.test123.de",
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "-u",
                "/images",
                "--ssl",
                "--extended-perfdata",
                "-j",
                "CONNECT",
                "--sni",
                "-b",
                Secret(1).unsafe("user:%s"),
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
                    {"cert_days": ("fixed", (10 * 3600 * 24, 20 * 3600 * 24))},
                ),
                "host": {
                    "address": ("direct", "www.test123.com"),
                    "port": 42,
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
                "mode": ("cert", {"cert_days": ("fixed", (10 * 3600 * 24, 20 * 3600 * 24))}),
                "host": {
                    "address": ("proxy", {"address": "p.roxy"}),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
                    {"cert_days": ("fixed", (10 * 3600 * 24, 20 * 3600 * 24))},
                ),
                "host": {
                    "address": ("proxy", {"address": "p.roxy"}),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
                    {"cert_days": ("fixed", (10 * 3600 * 24, 20 * 3600 * 24))},
                ),
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "[dead:beef::face]",
                            "port": 23,
                            "auth": {
                                "user": "user",
                                "password": Secret(2),
                            },
                        },
                    ),
                    "port": 42,
                    "virthost": "www.test123.com",
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "-C",
                "10,20",
                "--ssl",
                "-j",
                "CONNECT",
                "--sni",
                "-b",
                Secret(2).unsafe("user:%s"),
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
                "name": "irrelevant",
                "host": {
                    "address": ("proxy", {"address": "[dead:beef::face]", "port": 23}),
                    "port": 42,
                    "address_family": "ipv6_enforced",
                    "virthost": "www.test123.com",
                },
                "mode": ("cert", {"cert_days": ("fixed", (10 * 3600 * 24, 20 * 3600 * 24))}),
                "disable_sni": True,
            },
            HostConfig(
                name="hostname",
                ipv6_config=IPv6Config(
                    address="fe80::240",
                    additional_addresses=["fe80::241", "fe80::242", "fe80::243"],
                ),
            ),
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
                "name": "irrelevant",
                "host": {"address": ("direct", "www.test123.com")},
                "mode": ("url", {"ssl": "auto"}),
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
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
                "host": {
                    "virthost": "$to.expand.virthost$",
                    "address": ("direct", "$to.expand.address$"),
                },
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
                macros={
                    "$to.expand.virthost$": "expanded.virthost",
                    "$to.expand.address$": "expanded.address",
                },
            ),
            [
                "--sni",
                "-I",
                "expanded.address",
                "-H",
                "expanded.virthost",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {"virthost": "virtual.host"},
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "--sni",
                "-I",
                "1.2.3.4",
                "-H",
                "virtual.host",
            ],
        ),
        (
            {
                "name": "irrelevant",
                "mode": ("url", {}),
                "host": {"address_family": "primary_enforced"},
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "-4",
                "--sni",
                "-I",
                "1.2.3.4",
            ],
        ),
        pytest.param(
            {
                "name": "irrelevant",
                "host": {
                    "address": ("proxy", {"address": "proxy", "port": 123}),
                    "port": 43,
                    "address_family": "ipv6_enforced",
                },
                "mode": ("url", {}),
            },
            HostConfig(
                name="hostname",
                ipv6_config=IPv6Config(
                    address="fe80::240",
                    additional_addresses=["fe80::241", "fe80::242", "fe80::243"],
                ),
            ),
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
                "fe80::240:43",
            ],
            id="proxy + virtual host (which is ignored)",
        ),
        pytest.param(
            {
                "name": "myservice",
                "host": {
                    "address": ("direct", "checkmk.com"),
                    "port": 443,
                    "address_family": "ipv4_enforced",
                    "virthost": "virthost",
                },
                "mode": (
                    "url",
                    {
                        "uri": "/product",
                        "ssl": "ssl_1_2",
                        "response_time": ("fixed", (100.0 / 1000, 200.0 / 1000)),
                        "timeout": 10,
                        "user_agent": "user",
                        "add_headers": ["line1", "line2"],
                        "auth": {
                            "user": "user",
                            "password": Secret(3),
                        },
                        "onredirect": "warning",
                        "expect_response_header": "Product | Checkmk",
                        "expect_response": ["Checkmk"],
                        "expect_string": "checkmk",
                        "expect_regex": {
                            "regex": "checkmk",
                            "case_insensitive": True,
                            "crit_if_found": True,
                            "multiline": True,
                        },
                        "post_data": {"data": "data", "content_type": "text/html"},
                        "method": "GET",
                        "no_body": True,
                        "page_size": {"minimum": 1, "maximum": 500},
                        "max_age": 86400,
                        "urlize": True,
                        "extended_perfdata": True,
                    },
                ),
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "-u",
                "/product",
                "--ssl=1.2",
                "-w",
                "0.100000",
                "-c",
                "0.200000",
                "-t",
                "10",
                "-A",
                "user",
                "-k",
                "line1",
                "-k",
                "line2",
                "-a",
                Secret(3).unsafe("user:%s"),
                "--onredirect=warning",
                "-e",
                "Checkmk",
                "-s",
                "checkmk",
                "-d",
                "Product | Checkmk",
                "-l",
                "-R",
                "checkmk",
                "--invert-regex",
                "--extended-perfdata",
                "-P",
                "data",
                "-T",
                "text/html",
                "-j",
                "GET",
                "--no-body",
                "-m",
                "1:500",
                "-M",
                "86400",
                "-L",
                "-4",
                "--sni",
                "-p",
                "443",
                "-I",
                "checkmk.com",
                "-H",
                "virthost",
            ],
            id="check url, all params",
        ),
        pytest.param(
            {
                "name": "myservice",
                "host": {},
                "mode": (
                    "url",
                    {
                        "expect_regex": {
                            "regex": "checkmk",
                            "case_insensitive": False,
                            "crit_if_found": False,
                            "multiline": False,
                        }
                    },
                ),
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            ["-r", "checkmk", "--sni", "-I", "1.2.3.4"],
            id="check url, regex without additional options",
        ),
        pytest.param(
            {"name": "test-service", "host": {}, "mode": ("url", {})},
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            ["--sni", "-I", "1.2.3.4"],
            id="minimal",
        ),
        pytest.param(
            {
                "name": "test-service",
                "host": {
                    "address": (
                        "proxy",
                        {
                            "address": "test-proxy",
                            "port": 80,
                            "auth": {
                                "user": "test-user",
                                "password": Secret(4),
                            },
                        },
                    ),
                    "port": 443,
                    "address_family": "any",
                    "virthost": "test-host",
                },
                "mode": (
                    "url",
                    {
                        "uri": "/url.com",
                        "ssl": "ssl_1_1",
                        "response_time": ("fixed", (100000.0, 200000.0)),
                        "timeout": 10.0,
                        "user_agent": "test-agent",
                        "add_headers": ["header", "lines"],
                        "auth": {
                            "user": "test-user-2",
                            "password": Secret(5),
                        },
                        "onredirect": "critical",
                        "expect_response_header": "test-response-header",
                        "expect_response": ["test-response"],
                        "expect_string": "test-content",
                        "expect_regex": {
                            "regex": "test-regex",
                            "case_insensitive": True,
                            "crit_if_found": True,
                            "multiline": True,
                        },
                        "post_data": {"data": "test-post", "content_type": "text/html"},
                        "method": "POST",
                        "no_body": True,
                        "page_size": {"minimum": 1, "maximum": 500},
                        "max_age": 604800.0,
                        "urlize": True,
                        "extended_perfdata": True,
                    },
                ),
                "disable_sni": True,
            },
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            [
                "-u",
                "/url.com",
                "--ssl=1.1",
                "-w",
                "100000.000000",
                "-c",
                "200000.000000",
                "-t",
                "10",
                "-A",
                "test-agent",
                "-k",
                "header",
                "-k",
                "lines",
                "-a",
                Secret(5).unsafe("test-user-2:%s"),
                "--onredirect=critical",
                "-e",
                "test-response",
                "-s",
                "test-content",
                "-d",
                "test-response-header",
                "-l",
                "-R",
                "test-regex",
                "--invert-regex",
                "--extended-perfdata",
                "-P",
                "test-post",
                "-T",
                "text/html",
                "-j",
                "POST",
                "--no-body",
                "-m",
                "1:500",
                "-M",
                "604800",
                "-L",
                "-b",
                Secret(4).unsafe("test-user:%s"),
                "-p",
                "80",
                "-I",
                "test-proxy",
                "-H",
                "test-host:443",
            ],
            id="maximal",
        ),
    ],
)
def test_check_http_argument_parsing(
    params: Mapping[str, Any],
    host_config: HostConfig,
    expected_args: Sequence[object],
) -> None:
    """Tests if all required arguments are present."""
    (command,) = active_check_http(params, host_config)
    assert command.command_arguments == expected_args


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
    http_params = HttpParams.model_validate(params)
    assert (
        check_http_description(
            HostConfig(
                name="hostname",
                ipv4_config=IPv4Config(address="1.2.3.4"),
            ),
            http_params,
        )
        == expected_description
    )
