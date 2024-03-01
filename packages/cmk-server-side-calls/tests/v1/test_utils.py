#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Literal

import pytest

from cmk.server_side_calls.v1 import (
    HostConfig,
    HTTPProxy,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    noop_parser,
    parse_http_proxy,
    parse_secret,
    PlainTextSecret,
    replace_macros,
    Secret,
    StoredSecret,
)


@pytest.mark.parametrize(
    "secret, expected_result",
    [
        pytest.param(
            ("store", "stored_password_id"),
            StoredSecret(value="stored_password_id", format="%s"),
            id="stored password",
        ),
        pytest.param(
            ("password", "password1234"),
            PlainTextSecret(value="password1234", format="%s"),
            id="plain-text password",
        ),
    ],
)
def test_get_secret_from_params(
    secret: tuple[Literal["store", "password"], str], expected_result: Secret
) -> None:
    assert parse_secret(secret) == expected_result


def test_get_secret_from_params_invalid_type() -> None:
    with pytest.raises(ValueError, match="secret type has as to be either 'store' or 'password'"):
        parse_secret(("invalid", "password1234"))  # type: ignore[arg-type]


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
    http_proxies = {"test_proxy": HTTPProxy(id="test_proxy", name="Test", url="test.com")}

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
    http_proxies = {"test_proxy": HTTPProxy(id="test_proxy", name="Test", url="test.com")}

    with pytest.raises(ValueError, match=expected_error):
        parse_http_proxy(proxy, http_proxies)


def test_noop_parser() -> None:
    params = {"user": "test_user", "max_logs": 1000}
    assert noop_parser(params) == params


class TestIPConfig:
    def test_ipv4_family(self) -> None:
        assert IPv4Config(address="1.2.3.4").family is IPAddressFamily.IPV4

    def test_ipv6_family(self) -> None:
        assert IPv6Config(address="fe80::240").family is IPAddressFamily.IPV6

    def test_ipv4_raises(self) -> None:
        with pytest.raises(RuntimeError):
            _ = IPv4Config(address=None).address

    def test_ipv6_raises(self) -> None:
        with pytest.raises(RuntimeError):
            _ = IPv6Config(address=None).address


class TestHostConfig:
    def test_alias(self) -> None:
        assert HostConfig(name="my_name").alias is "my_name"

    def test_primary_raises(self) -> None:
        with pytest.raises(ValueError):
            _ = HostConfig(name="my_name").primary_ip_config

    def test_host_config_eq(self) -> None:
        assert HostConfig(name="my_name", alias="my_alias") != HostConfig(name="my_name")
        assert HostConfig(name="my_name") == HostConfig(name="my_name")


@pytest.mark.parametrize(
    "string, expected_result",
    [
        pytest.param("", "", id="empty"),
        pytest.param("Text without macros", "Text without macros", id="without macros"),
        pytest.param("My host $HOST_ALIAS$", "My host host_alias", id="one macro"),
        pytest.param(
            "-H $HOST_NAME$ -4 $HOST_IPV4_ADDRESS$ -6 $HOST_IPV6_ADDRESS$",
            "-H hostname -4 0.0.0.1 -6 fe80::240",
            id="multiple macros",
        ),
        pytest.param("ID$HOST_TAG_tag1$000", "ID55000", id="double replacement"),
    ],
)
def test_replace_macros(string: str, expected_result: str) -> None:
    macros = {
        "$HOST_NAME$": "hostname",
        "$HOST_ADDRESS$": "0.0.0.1",
        "$HOST_ALIAS$": "host_alias",
        "$HOST_IPV4_ADDRESS$": "0.0.0.1",
        "$HOST_IPV6_ADDRESS$": "fe80::240",
        "$HOST_TAG_tag1$": "$HOST_TAG_tag2$",
        "$HOST_TAG_tag2$": "55",
    }
    assert replace_macros(string, macros) == expected_result
