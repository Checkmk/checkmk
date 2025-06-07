#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Sequence

import pytest

from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils import ip_lookup

import cmk.base.config as base_config

from cmk.server_side_calls.v1 import HostConfig, IPAddressFamily, IPv4Config, IPv6Config


def make_config_cache_mock(
    *,
    additional_ipaddresses: tuple[Sequence[str], Sequence[str]],
    ip_stack: ip_lookup.IPStackConfig,
    family: socket.AddressFamily,
) -> object:
    class ConfigCacheMock:
        @staticmethod
        def ip_stack_config(host_name: str) -> ip_lookup.IPStackConfig:
            return ip_stack

        @staticmethod
        def default_address_family(host_name: str) -> socket.AddressFamily:
            return family

        @staticmethod
        def additional_ipaddresses(host_name: str) -> tuple[Sequence[str], Sequence[str]]:
            return additional_ipaddresses

        @staticmethod
        def alias(host_name: str) -> str:
            return "host alias"

    return ConfigCacheMock()


def mock_ip_address_of(
    host_name: HostName,
    family: socket.AddressFamily | None = None,
) -> HostAddress:
    if family == socket.AF_INET6:
        return HostAddress("::1")
    return HostAddress("0.0.0.1")


def test_get_host_config_macros_stringified() -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([], []),
        ip_stack=ip_lookup.IPStackConfig.NO_IP,
        family=socket.AddressFamily.AF_INET,
    )

    host_name = HostName("host_name")
    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(  # type: ignore[attr-defined]
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),  # type: ignore[attr-defined]
        config_cache.default_address_family(host_name),  # type: ignore[attr-defined]
        config_cache.ip_stack_config(host_name),  # type: ignore[attr-defined]
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        {"$HOST_EC_SL$": 30},
        mock_ip_address_of,
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        macros={"$HOST_EC_SL$": "30"},
    )


def test_get_host_config_no_ip() -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("ignore.v4.noip")], [HostAddress("ignore.v6.noip")]),
        ip_stack=ip_lookup.IPStackConfig.NO_IP,
        family=socket.AddressFamily.AF_INET6,
    )

    host_name = HostName("host_name")
    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(  # type: ignore[attr-defined]
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),  # type: ignore[attr-defined]
        config_cache.default_address_family(host_name),  # type: ignore[attr-defined]
        config_cache.ip_stack_config(host_name),  # type: ignore[attr-defined]
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        {},
        mock_ip_address_of,
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )


def test_get_host_config_ipv4(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("1.2.3.4")], [HostAddress("ignore.v6.noip")]),
        ip_stack=ip_lookup.IPStackConfig.IPv4,
        family=socket.AddressFamily.AF_INET,
    )

    host_name = HostName("host_name")
    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(  # type: ignore[attr-defined]
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),  # type: ignore[attr-defined]
        config_cache.default_address_family(host_name),  # type: ignore[attr-defined]
        config_cache.ip_stack_config(host_name),  # type: ignore[attr-defined]
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        {},
        mock_ip_address_of,
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv4_config=IPv4Config(
            address="0.0.0.1",
            additional_addresses=["1.2.3.4"],
        ),
        primary_family=IPAddressFamily.IPV4,
        macros={},
    )


def test_get_host_config_ipv6(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("ignore.v4.ipv6")], [HostAddress("::42")]),
        ip_stack=ip_lookup.IPStackConfig.IPv6,
        family=socket.AddressFamily.AF_INET6,
    )

    host_name = HostName("host_name")
    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(  # type: ignore[attr-defined]
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),  # type: ignore[attr-defined]
        config_cache.default_address_family(host_name),  # type: ignore[attr-defined]
        config_cache.ip_stack_config(host_name),  # type: ignore[attr-defined]
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        {},
        mock_ip_address_of,
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv6_config=IPv6Config(
            address="::1",
            additional_addresses=["::42"],
        ),
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )


def test_get_host_config_dual(monkeypatch: pytest.MonkeyPatch) -> None:
    config_cache = make_config_cache_mock(
        additional_ipaddresses=([HostAddress("2.3.4.2")], [HostAddress("::42")]),
        ip_stack=ip_lookup.IPStackConfig.DUAL_STACK,
        family=socket.AddressFamily.AF_INET6,
    )

    host_name = HostName("host_name")
    additional_addresses_ipv4, additional_addresses_ipv6 = config_cache.additional_ipaddresses(  # type: ignore[attr-defined]
        host_name
    )
    host_config = base_config.get_ssc_host_config(
        host_name,
        config_cache.alias(host_name),  # type: ignore[attr-defined]
        config_cache.default_address_family(host_name),  # type: ignore[attr-defined]
        config_cache.ip_stack_config(host_name),  # type: ignore[attr-defined]
        additional_addresses_ipv4,
        additional_addresses_ipv6,
        {},
        mock_ip_address_of,
    )

    assert host_config == HostConfig(
        name="host_name",
        alias="host alias",
        ipv4_config=IPv4Config(
            address="0.0.0.1",
            additional_addresses=["2.3.4.2"],
        ),
        ipv6_config=IPv6Config(
            address="::1",
            additional_addresses=["::42"],
        ),
        primary_family=IPAddressFamily.IPV6,
        macros={},
    )
