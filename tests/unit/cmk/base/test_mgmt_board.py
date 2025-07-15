#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Mapping
from typing import Literal

import pytest
from pytest import MonkeyPatch

# No stub file
from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.hostaddress import HostName


@pytest.mark.parametrize(
    "protocol,cred_attribute,credentials",
    [
        ("snmp", "management_snmp_credentials", "HOST"),
        (
            "ipmi",
            "management_ipmi_credentials",
            {
                "username": "USER",
                "password": "PASS",
            },
        ),
    ],
)
def test_mgmt_explicit_settings(
    monkeypatch: MonkeyPatch,
    protocol: Literal["snmp", "ipmi"],
    cred_attribute: str,
    credentials: str | Mapping[str, str],
) -> None:
    host = HostName("mgmt-host")

    ts = Scenario()
    ts.add_host(host)
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: protocol})
    ts.set_option(cred_attribute, {host: credentials})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host)
    assert config_cache.management_protocol(host) == protocol
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.1"
    assert config_cache.management_credentials(host, protocol) == credentials


def test_mgmt_explicit_address(monkeypatch: MonkeyPatch) -> None:
    host = HostName("mgmt-host")

    ts = Scenario()
    ts.add_host(host)
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: "snmp"})
    ts.set_option("host_attributes", {host: {"management_address": "127.0.0.2"}})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host)
    assert config_cache.management_protocol(host) == "snmp"
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.2"
    assert config_cache.management_credentials(host, "snmp") == "public"


def test_mgmt_disabled(monkeypatch: MonkeyPatch) -> None:
    host = HostName("mgmt-host")

    ts = Scenario()
    ts.add_host(host)
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: None})
    ts.set_option("host_attributes", {host: {"management_address": "127.0.0.1"}})
    ts.set_option("management_snmp_credentials", {host: "HOST"})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host) is False
    assert config_cache.management_protocol(host) is None
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.1"


@pytest.mark.parametrize(
    "protocol,cred_attribute,credentials,ruleset_credentials",
    [
        ("snmp", "management_snmp_credentials", "HOST", "RULESET"),
        (
            "ipmi",
            "management_ipmi_credentials",
            {
                "username": "USER",
                "password": "PASS",
            },
            {
                "username": "RULESETUSER",
                "password": "RULESETPASS",
            },
        ),
    ],
)
def test_mgmt_config_ruleset(
    monkeypatch, protocol, cred_attribute, credentials, ruleset_credentials
):
    ts = Scenario()
    ts.set_ruleset(
        "management_board_config",
        [
            {
                "condition": {},
                "id": "00",
                "options": {},
                "value": (protocol, ruleset_credentials),
            },
        ],
    )

    host = HostName("mgmt-host")
    ts.add_host(host, host_path="/wato/folder1/hosts.mk")
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: protocol})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host)
    assert config_cache.management_protocol(host) == protocol
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.1"
    assert config_cache.management_credentials(host, protocol) == ruleset_credentials


@pytest.mark.parametrize(
    "protocol,cred_attribute,folder_credentials,ruleset_credentials",
    [
        ("snmp", "management_snmp_credentials", "FOLDER", "RULESET"),
        (
            "ipmi",
            "management_ipmi_credentials",
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
            {
                "username": "RULESETUSER",
                "password": "RULESETPASS",
            },
        ),
    ],
)
def test_mgmt_config_ruleset_order(
    monkeypatch, protocol, cred_attribute, folder_credentials, ruleset_credentials
):
    ts = Scenario()
    ts.set_ruleset(
        "management_board_config",
        [
            {
                "condition": {},
                "options": {},
                "id": "01",
                "value": ("snmp", "RULESET1"),
            },
            {
                "condition": {},
                "options": {},
                "id": "02",
                "value": ("snmp", "RULESET2"),
            },
        ],
    )

    host = HostName("mgmt-host")
    ts.add_host(host, host_path="/wato/folder1/hosts.mk")
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: "snmp"})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host)
    assert config_cache.management_protocol(host) == "snmp"
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.1"
    assert config_cache.management_credentials(host, "snmp") == "RULESET1"


@pytest.mark.parametrize(
    "protocol,cred_attribute,host_credentials,ruleset_credentials",
    [
        ("snmp", "management_snmp_credentials", "FOLDER", "RULESET"),
        (
            "ipmi",
            "management_ipmi_credentials",
            {
                "username": "FOLDERUSER",
                "password": "FOLDERPASS",
            },
            {
                "username": "RULESETUSER",
                "password": "RULESETPASS",
            },
        ),
    ],
)
def test_mgmt_config_ruleset_overidden_by_explicit_setting(
    monkeypatch, protocol, cred_attribute, host_credentials, ruleset_credentials
):
    ts = Scenario()
    ts.set_ruleset(
        "management_board_config",
        [
            {
                "condition": {},
                "id": "01",
                "options": {},
                "value": (protocol, ruleset_credentials),
            },
        ],
    )

    host = HostName("mgmt-host")
    ts.add_host(host, host_path="/wato/folder1/hosts.mk")
    ts.set_option("ipaddresses", {host: "127.0.0.1"})
    ts.set_option("management_protocol", {host: protocol})
    ts.set_option(cred_attribute, {host: host_credentials})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.has_management_board(host)
    assert config_cache.management_protocol(host) == protocol
    assert config_cache.management_address(host, socket.AddressFamily.AF_INET) == "127.0.0.1"
    assert config_cache.management_credentials(host, protocol) == host_credentials


@pytest.mark.parametrize(
    "protocol, cred_attribute, credentials",
    [
        ("snmp", "management_snmp_credentials", "HOST"),
        (
            "ipmi",
            "management_ipmi_credentials",
            {
                "username": "USER",
                "password": "PASS",
            },
        ),
    ],
)
@pytest.mark.parametrize(
    "tags, host_attributes, ipaddresses, ipv6addresses, ip_address_result",
    [
        ({}, {}, {}, {}, None),
        # Explicit management_address
        ({}, {"management_address": "127.0.0.1"}, {}, {}, "127.0.0.1"),
        (
            {
                "address_family": "ip-v4-only",
            },
            {"management_address": "127.0.0.1"},
            {},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v6-only",
            },
            {"management_address": "127.0.0.1"},
            {},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v4v6",
            },
            {"management_address": "127.0.0.1"},
            {},
            {},
            "127.0.0.1",
        ),
        # Explicit management_address + ipaddresses
        ({}, {"management_address": "127.0.0.1"}, {"mgmt-host": "127.0.0.2"}, {}, "127.0.0.1"),
        (
            {
                "address_family": "ip-v4-only",
            },
            {"management_address": "127.0.0.1"},
            {"mgmt-host": "127.0.0.2"},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v6-only",
            },
            {"management_address": "127.0.0.1"},
            {"mgmt-host": "127.0.0.2"},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v4v6",
            },
            {"management_address": "127.0.0.1"},
            {"mgmt-host": "127.0.0.2"},
            {},
            "127.0.0.1",
        ),
        # Explicit management_address + ipv6addresses
        ({}, {"management_address": "127.0.0.1"}, {}, {"mgmt-host": "::2"}, "127.0.0.1"),
        (
            {
                "address_family": "ip-v4-only",
            },
            {"management_address": "127.0.0.1"},
            {},
            {"mgmt-host": "::2"},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v6-only",
            },
            {"management_address": "127.0.0.1"},
            {},
            {"mgmt-host": "::2"},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v4v6",
            },
            {"management_address": "127.0.0.1"},
            {},
            {"mgmt-host": "::2"},
            "127.0.0.1",
        ),
        # ipv4 host
        (
            {
                "address_family": "ip-v4-only",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v4-only",
            },
            {},
            {},
            {"mgmt-host": "::1"},
            None,
        ),
        (
            {
                "address_family": "ip-v4-only",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {"mgmt-host": "::1"},
            "127.0.0.1",
        ),
        # ipv6 host
        (
            {
                "address_family": "ip-v6-only",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {},
            None,
        ),
        (
            {
                "address_family": "ip-v6-only",
            },
            {},
            {},
            {"mgmt-host": "::1"},
            "::1",
        ),
        (
            {
                "address_family": "ip-v6-only",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {"mgmt-host": "::1"},
            "::1",
        ),
        # dual host
        (
            {
                "address_family": "ip-v4v6",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {},
            "127.0.0.1",
        ),
        (
            {
                "address_family": "ip-v4v6",
            },
            {},
            {},
            {"mgmt-host": "::1"},
            None,
        ),
        (
            {
                "address_family": "ip-v4v6",
            },
            {},
            {"mgmt-host": "127.0.0.1"},
            {"mgmt-host": "::1"},
            "127.0.0.1",
        ),
    ],
)
def test_mgmt_board_ip_addresses(
    monkeypatch,
    protocol,
    cred_attribute,
    credentials,
    tags,
    host_attributes,
    ipaddresses,
    ipv6addresses,
    ip_address_result,
):
    hostname = HostName("mgmt-host")

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_option("host_attributes", {hostname: host_attributes})
    ts.set_option("ipaddresses", ipaddresses)
    ts.set_option("ipv6addresses", ipv6addresses)
    ts.set_option("management_protocol", {hostname: protocol})
    ts.set_option(cred_attribute, {hostname: credentials})

    config_cache = ts.apply(monkeypatch)
    ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6] = (
        socket.AddressFamily.AF_INET6
        if tags.get("address_family") == "ip-v6-only"
        else socket.AddressFamily.AF_INET
    )
    assert config_cache.has_management_board(hostname)
    assert config_cache.management_protocol(hostname) == protocol
    assert config_cache.management_address(hostname, ip_family) == ip_address_result
    assert config_cache.management_credentials(hostname, protocol) == credentials
