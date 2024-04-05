#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    NetworkAddressConfig,
    noop_parser,
    parse_http_proxy,
    parse_secret,
    PlainTextSecret,
    ResolvedIPAddressFamily,
    Secret,
    StoredSecret,
)


@pytest.mark.parametrize(
    "secret, expected_result",
    [
        pytest.param(
            ("store", "stored_password_id"),
            StoredSecret("stored_password_id", format="%s"),
            id="stored password",
        ),
        pytest.param(
            ("password", "password1234"),
            PlainTextSecret("password1234", format="%s"),
            id="plain-text password",
        ),
    ],
)
def test_get_secret_from_params(secret: object, expected_result: Secret) -> None:
    assert parse_secret(secret) == expected_result


def test_get_secret_from_params_invalid_type() -> None:
    with pytest.raises(ValueError, match="secret type has as to be either 'store' or 'password'"):
        parse_secret(("invalid", "password1234"))


@pytest.mark.parametrize(
    "proxy, expected_result",
    [
        pytest.param(
            ("global", "test_proxy"),
            "test.com",
            id="global proxy",
        ),
        pytest.param(
            ("global", "missing_proxy"),
            "FROM_ENVIRONMENT",
            id="missing global proxy",
        ),
        pytest.param(
            ("url", "proxy.com"),
            "proxy.com",
            id="url proxy",
        ),
        pytest.param(
            ("environment", "environment"),
            "FROM_ENVIRONMENT",
            id="environment proxy",
        ),
        pytest.param(
            ("no_proxy", None),
            "NO_PROXY",
            id="no proxy",
        ),
    ],
)
def test_get_http_proxy(
    proxy: object,
    expected_result: str,
) -> None:
    http_proxies = {"test_proxy": HTTPProxy("test_proxy", "Test", "test.com")}

    assert parse_http_proxy(proxy, http_proxies) == expected_result


@pytest.mark.parametrize(
    "proxy, expected_error",
    [
        pytest.param(
            ("invalid", None),
            "proxy type has to be one of: 'global', 'environment', 'url' or 'no_proxy'",
            id="invalid proxy type",
        ),
        pytest.param(
            {"proxy": "test_proxy"},
            "proxy object has to be a tuple",
            id="invalid proxy",
        ),
        pytest.param(
            ("global", 123),
            "proxy value has to be a string or None",
            id="invalid proxy value",
        ),
    ],
)
def test_get_http_proxy_value_error(
    proxy: object,
    expected_error: str,
) -> None:
    http_proxies = {"test_proxy": HTTPProxy("test_proxy", "Test", "test.com")}

    with pytest.raises(ValueError, match=expected_error):
        parse_http_proxy(proxy, http_proxies)


def test_noop_parser() -> None:
    params = {"user": "test_user", "max_logs": 1000}
    assert noop_parser(params) == params


@pytest.mark.parametrize(
    "host_config, expected_all_ipv4, expected_all_ipv6",
    [
        pytest.param(
            HostConfig(
                name="hostname",
                resolved_address="0.0.0.1",
                alias="host_alias",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
                address_config=NetworkAddressConfig(
                    ip_family=IPAddressFamily.DUAL_STACK,
                    ipv4_address="0.0.0.2",
                    ipv6_address="fe80::240",
                    additional_ipv4_addresses=["0.0.0.4", "0.0.0.5"],
                    additional_ipv6_addresses=[
                        "fe80::241",
                        "fe80::242",
                        "fe80::243",
                    ],
                ),
            ),
            ["0.0.0.2", "0.0.0.4", "0.0.0.5"],
            ["fe80::240", "fe80::241", "fe80::242", "fe80::243"],
            id="ipv4address and ipv6address present",
        ),
        pytest.param(
            HostConfig(
                name="hostname",
                resolved_address="0.0.0.1",
                alias="host_alias",
                resolved_ip_family=ResolvedIPAddressFamily.IPV4,
                address_config=NetworkAddressConfig(
                    ip_family=IPAddressFamily.DUAL_STACK,
                    ipv4_address=None,
                    ipv6_address=None,
                    additional_ipv4_addresses=["0.0.0.4", "0.0.0.5"],
                    additional_ipv6_addresses=[
                        "fe80::241",
                        "fe80::242",
                        "fe80::243",
                    ],
                ),
            ),
            ["0.0.0.4", "0.0.0.5"],
            ["fe80::241", "fe80::242", "fe80::243"],
            id="ipv4address and ipv6address not present",
        ),
    ],
)
def test_host_config_properties(
    host_config: HostConfig, expected_all_ipv4: Sequence[str], expected_all_ipv6: Sequence[str]
) -> None:
    assert host_config.address_config.all_ipv4_addresses == expected_all_ipv4
    assert host_config.address_config.all_ipv6_addresses == expected_all_ipv6
