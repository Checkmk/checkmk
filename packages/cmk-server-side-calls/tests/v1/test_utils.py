#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.server_side_calls.v1 import (
    HostConfig,
    IPAddressFamily,
    IPv4Config,
    IPv6Config,
    noop_parser,
    replace_macros,
)


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
        assert HostConfig(name="my_name").alias == "my_name"

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
