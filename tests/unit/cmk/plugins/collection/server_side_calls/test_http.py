#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.plugins.collection.server_side_calls.http import (
    active_check_http,
    DirectHost,
    Family,
    HostSettings,
    HTTPParams,
    ProxyHost,
    ProxySettings,
    URLMode,
)
from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    NetworkAddressConfig,
    PlainTextSecret,
    ResolvedIPAddressFamily,
    StoredSecret,
)

HOST_CONFIG = HostConfig(
    name="hostname",
    resolved_address="0.0.0.1",
    alias="host_alias",
    resolved_ip_family=ResolvedIPAddressFamily.IPV4,
    address_config=NetworkAddressConfig(
        ipv4_address="0.0.0.2",
        ipv6_address="fe80::240",
        additional_ipv4_addresses=["0.0.0.4", "0.0.0.5"],
        additional_ipv6_addresses=[
            "fe80::241",
            "fe80::242",
            "fe80::243",
        ],
        ip_family=IPAddressFamily.DUAL_STACK,
    ),
)


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
                PlainTextSecret(value="pwd", format="user:%s"),
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
                StoredSecret(value="check_http", format="user:%s"),
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
                "name": "irrelevant",
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
                "0.0.0.2",
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
                "0.0.0.2",
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
                        "ssl": "1.2",
                        "response_time": (100.0, 200.0),
                        "timeout": 10,
                        "user_agent": "user",
                        "add_headers": ["line1", "line2"],
                        "auth": ("user", ("password", "password")),
                        "onredirect": "warning",
                        "expect_response_header": "Product | Checkmk",
                        "expect_response": ["Checkmk"],
                        "expect_string": "checkmk",
                        "expect_regex": ("checkmk", True, True, True),
                        "post_data": ("data", "text/html"),
                        "method": "GET",
                        "no_body": True,
                        "page_size": (1, 500),
                        "max_age": 86400,
                        "urlize": True,
                        "extended_perfdata": True,
                    },
                ),
            },
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
                PlainTextSecret(value="password", format="user:%s"),
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
                "mode": ("url", {"expect_regex": ("checkmk", False, False, False)}),
            },
            ["-r", "checkmk", "--sni", "-I", "0.0.0.2"],
            id="check url, regex without additional options",
        ),
    ],
)
def test_check_http_argument_parsing(
    params: Mapping[str, Any],
    expected_args: Sequence[object],
) -> None:
    """Tests if all required arguments are present."""
    parsed_params = active_check_http.parameter_parser(params)
    commands = list(active_check_http.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].command_arguments == expected_args


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
    parsed_params = active_check_http.parameter_parser(params)
    commands = list(active_check_http.commands_function(parsed_params, HOST_CONFIG, {}))

    assert len(commands) == 1
    assert commands[0].service_description == expected_description


@pytest.mark.parametrize(
    "params, expected_result",
    [
        (
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
                        "ssl": "1.2",
                        "response_time": (100.0, 200.0),
                        "timeout": 10,
                        "user_agent": "user",
                        "add_headers": ["line1", "line2"],
                        "auth": ("user", ("password", "password")),
                        "onredirect": "warning",
                        "expect_response_header": "Product | Checkmk",
                        "expect_response": ["Checkmk"],
                        "expect_string": "checkmk",
                        "expect_regex": ("checkmk", True, True, True),
                        "post_data": ("data", "text/html"),
                        "method": "GET",
                        "no_body": True,
                        "page_size": (1, 500),
                        "max_age": 86400,
                        "urlize": True,
                        "extended_perfdata": True,
                    },
                ),
            },
            HTTPParams(
                name="myservice",
                host=DirectHost(
                    address="checkmk.com",
                    settings=HostSettings(port=443, family=Family.enforce_ipv4, virtual="virthost"),
                ),
                mode=URLMode(
                    uri="/product",
                    ssl="1.2",
                    response_time=(100.0, 200.0),
                    timeout=10,
                    user_agent="user",
                    add_headers=["line1", "line2"],
                    auth=("user", ("password", "password")),
                    onredirect="warning",
                    expect_response_header="Product | Checkmk",
                    expect_response=["Checkmk"],
                    expect_string="checkmk",
                    expect_regex=("checkmk", True, True, True),
                    post_data=("data", "text/html"),
                    method="GET",
                    no_body=True,
                    page_size=(1, 500),
                    max_age=86400,
                    urlize=True,
                    extended_perfdata=True,
                ),
            ),
        )
    ],
)
def test_parse_http_params(params: Mapping[str, object], expected_result: HTTPParams) -> None:
    assert active_check_http.parameter_parser(params) == expected_result


@pytest.mark.parametrize(
    "virtual, is_url_mode, expected_address",
    [
        pytest.param("0.0.0.1", True, "0.0.0.1", id="virtual address, url mode"),
        pytest.param("0.0.0.1", False, "0.0.0.1", id="virtual address, not url mode"),
        pytest.param(None, True, None, id="no virtual address, url mode"),
        pytest.param(None, False, "127.0.0.1", id="direct host address"),
        pytest.param("$HOSTNAME$", True, "hostname", id="virtual address with macro, url mode"),
        pytest.param("$HOSTNAME$", False, "hostname", id="virtual address with macro, no url mode"),
    ],
)
def test_direct_host_virtual_host(
    virtual: str | None, is_url_mode: bool, expected_address: str | None
) -> None:
    host_settings = HostSettings(443, None, virtual)
    direct_host = DirectHost("127.0.0.1", host_settings)

    assert direct_host.virtual_host(is_url_mode, HOST_CONFIG) == expected_address


@pytest.mark.parametrize(
    "virtual, port, expected_address",
    [
        pytest.param("0.0.0.1", 443, "0.0.0.1:443", id="virtual address, port"),
        pytest.param("0.0.0.1", None, "0.0.0.1", id="virtual address, no port"),
        pytest.param(None, 443, "0.0.0.2:443", id="host config address, port"),
        pytest.param(None, None, "0.0.0.2", id="host config address, no port"),
        pytest.param("$HOSTNAME$", 443, "hostname:443", id="virtual address with macro, port"),
        pytest.param("$HOSTNAME$", None, "hostname", id="virtual address with macro, no port"),
    ],
)
def test_proxy_host_virtual_host(
    virtual: str | None, port: int | None, expected_address: str | None
) -> None:
    proxy_settings = ProxySettings("8.8.8.8", None, None)
    host_settings = HostSettings(port, None, virtual)
    proxy_host = ProxyHost(proxy_settings, host_settings)

    assert proxy_host.virtual_host(True, HOST_CONFIG) == expected_address
