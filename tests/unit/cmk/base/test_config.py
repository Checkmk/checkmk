#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import re
import shutil
import socket
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, Final, Literal

import pytest
from pytest import MonkeyPatch

from tests.testlib.base import Scenario

import cmk.utils.paths
import cmk.utils.piggyback as piggyback
import cmk.utils.version as cmk_version
from cmk.utils.config_path import VersionedConfigPath
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.hostaddress import HostName
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import RulesetMatchObject, RuleSpec
from cmk.utils.sectionname import SectionName
from cmk.utils.tags import TagGroupID, TagID

from cmk.snmplib import SNMPBackendEnum

from cmk.fetchers import Mode, TCPEncryptionHandling

from cmk.checkengine.checking import CheckPluginName, ConfiguredService, ServiceID
from cmk.checkengine.discovery import AutocheckEntry, DiscoveryCheckParameters
from cmk.checkengine.inventory import InventoryPlugin
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.sectionparser import ParsedSectionName

import cmk.base.api.agent_based.register as agent_based_register
import cmk.base.config as config
from cmk.base.api.agent_based.plugin_classes import CheckPlugin as CheckPluginAPI
from cmk.base.api.agent_based.plugin_classes import SNMPSectionPlugin
from cmk.base.api.agent_based.register.utils_legacy import LegacyCheckDefinition
from cmk.base.config import ConfigCache, ip_address_of
from cmk.base.ip_lookup import AddressFamily

from cmk.agent_based.v1 import HostLabel


def test_all_offline_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.add_host(HostName("blub"), tags={TagGroupID("criticality"): TagID("offline")})
    ts.add_host(HostName("bla"))
    config_cache = ts.apply(monkeypatch)
    assert not [
        hn
        for hn in config_cache.hosts_config.hosts
        if config_cache.is_active(hn) and config_cache.is_offline(hn)
    ]


def test_all_offline_hosts_with_wato_default_config(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.set_ruleset(
        "only_hosts",
        [
            {
                "id": "01",
                "condition": {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("offline")}}},
                "value": True,
            },
        ],
    )
    ts.add_host(HostName("blub1"), tags={TagGroupID("criticality"): TagID("offline")})
    ts.add_host(
        HostName("blub2"),
        tags={TagGroupID("criticality"): TagID("offline"), TagGroupID("site"): TagID("site2")},
    )
    ts.add_host(HostName("bla"))
    config_cache = ts.apply(monkeypatch)
    assert [
        hn
        for hn in config_cache.hosts_config.hosts
        if config_cache.is_active(hn) and config_cache.is_offline(hn)
    ] == ["blub1"]


def test_all_configured_offline_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.set_ruleset(
        "only_hosts",
        [
            {
                "id": "01",
                "condition": {"host_tags": {TagGroupID("criticality"): {"$ne": TagID("offline")}}},
                "value": True,
            },
        ],
    )
    ts.add_host(
        HostName("blub1"),
        tags={TagGroupID("criticality"): TagID("offline"), TagGroupID("site"): TagID("site1")},
    )
    ts.add_host(
        HostName("blub2"),
        tags={TagGroupID("criticality"): TagID("offline"), TagGroupID("site"): TagID("site2")},
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        hn
        for hn in config_cache.hosts_config.hosts
        if config_cache.is_active(hn) and config_cache.is_offline(hn)
    ] == ["blub1"]


def test_all_configured_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("real1"), tags={TagGroupID("site"): TagID("site1")})
    ts.add_host(HostName("real2"), tags={TagGroupID("site"): TagID("site2")})
    ts.add_host(HostName("real3"))
    ts.add_cluster(
        HostName("cluster1"), tags={TagGroupID("site"): TagID("site1")}, nodes=[HostName("node1")]
    )
    ts.add_cluster(
        HostName("cluster2"), tags={TagGroupID("site"): TagID("site2")}, nodes=[HostName("node2")]
    )
    ts.add_cluster(HostName("cluster3"), nodes=[HostName("node3")])

    config_cache = ts.apply(monkeypatch)
    hosts_config = config_cache.hosts_config
    assert set(hosts_config.clusters) == {
        HostName("cluster1"),
        HostName("cluster2"),
        HostName("cluster3"),
    }
    assert set(hosts_config.hosts) == {
        HostName("real1"),
        HostName("real2"),
        HostName("real3"),
    }
    assert set(
        itertools.chain(hosts_config.clusters, hosts_config.hosts, hosts_config.shadow_hosts)
    ) == {
        HostName("cluster1"),
        HostName("cluster2"),
        HostName("cluster3"),
        HostName("real1"),
        HostName("real2"),
        HostName("real3"),
    }


def test_all_active_hosts(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario(site_id="site1")
    ts.add_host(HostName("real1"), tags={TagGroupID("site"): TagID("site1")})
    ts.add_host(HostName("real2"), tags={TagGroupID("site"): TagID("site2")})
    ts.add_host(HostName("real3"))
    ts.add_cluster(
        HostName("cluster1"), tags={TagGroupID("site"): TagID("site1")}, nodes=[HostName("node1")]
    )
    ts.add_cluster(
        HostName("cluster2"), tags={TagGroupID("site"): TagID("site2")}, nodes=[HostName("node2")]
    )
    ts.add_cluster(HostName("cluster3"), nodes=[HostName("node3")])

    config_cache = ts.apply(monkeypatch)
    hosts_config = config_cache.hosts_config
    assert {
        hn
        for hn in hosts_config.clusters
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    } == {HostName("cluster1"), HostName("cluster3")}
    assert {
        hn for hn in hosts_config.hosts if config_cache.is_active(hn) and config_cache.is_online(hn)
    } == {HostName("real1"), HostName("real3")}
    assert {
        hn
        for hn in itertools.chain(hosts_config.hosts, hosts_config.clusters)
        if config_cache.is_active(hn) and config_cache.is_online(hn)
    } == {HostName("cluster1"), HostName("cluster3"), HostName("real1"), HostName("real3")}


def test_config_cache_tag_to_group_map(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_option(
        "tag_config",
        {
            "aux_tags": [],
            "tag_groups": [
                {
                    "id": "dingeling",
                    "title": "Dung",
                    "tags": [
                        {"aux_tags": [], "id": TagID("dong"), "title": "ABC"},
                    ],
                }
            ],
        },
    )
    ts.apply(monkeypatch)
    assert ConfigCache.get_tag_to_group_map() == {
        TagID("all-agents"): TagGroupID("agent"),
        TagID("auto-piggyback"): TagGroupID("piggyback"),
        TagID("cmk-agent"): TagGroupID("agent"),
        TagID("checkmk-agent"): TagGroupID("checkmk-agent"),
        TagID("dong"): TagGroupID("dingeling"),
        TagID("ip-v4"): TagGroupID("ip-v4"),
        TagID("ip-v4-only"): TagGroupID("address_family"),
        TagID("ip-v4v6"): TagGroupID("address_family"),
        TagID("ip-v6"): TagGroupID("ip-v6"),
        TagID("ip-v6-only"): TagGroupID("address_family"),
        TagID("no-agent"): TagGroupID("agent"),
        TagID("no-ip"): TagGroupID("address_family"),
        TagID("no-piggyback"): TagGroupID("piggyback"),
        TagID("no-snmp"): TagGroupID("snmp_ds"),
        TagID("piggyback"): TagGroupID("piggyback"),
        TagID("ping"): TagGroupID("ping"),
        TagID("snmp"): TagGroupID("snmp"),
        TagID("snmp-v1"): TagGroupID("snmp_ds"),
        TagID("snmp-v2"): TagGroupID("snmp_ds"),
        TagID("special-agents"): TagGroupID("agent"),
        TagID("tcp"): TagGroupID("tcp"),
    }


@pytest.mark.parametrize(
    "hostname,host_path,result",
    [
        (HostName("none"), "/hosts.mk", 0),
        (HostName("main"), "/wato/hosts.mk", 0),
        (HostName("sub1"), "/wato/level1/hosts.mk", 1),
        (HostName("sub2"), "/wato/level1/level2/hosts.mk", 2),
        (HostName("sub3"), "/wato/level1/level3/hosts.mk", 3),
        (HostName("sub11"), "/wato/level11/hosts.mk", 11),
        (HostName("sub22"), "/wato/level11/level22/hosts.mk", 22),
    ],
)
def test_host_folder_matching(
    monkeypatch: MonkeyPatch, hostname: HostName, host_path: str, result: int
) -> None:
    ts = Scenario()
    ts.add_host(hostname, host_path=host_path)
    ts.set_ruleset(
        "agent_ports",
        [
            {"id": "01", "condition": {"host_folder": "/wato/level11/level22/"}, "value": 22},
            {"id": "02", "condition": {"host_folder": "/wato/level11/"}, "value": 11},
            {"id": "03", "condition": {"host_folder": "/wato/level1/level3/"}, "value": 3},
            {"id": "04", "condition": {"host_folder": "/wato/level1/level2/"}, "value": 2},
            {"id": "05", "condition": {"host_folder": "/wato/level1/"}, "value": 1},
            {"id": "06", "condition": {}, "value": 0},
        ],
    )

    config_cache = ts.apply(monkeypatch)
    assert config_cache._agent_port(hostname) == result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4-only")}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4v6")}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v6-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("no-ip")}, False),
    ],
)
def test_is_ipv4_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert (AddressFamily.IPv4 in config_cache.address_family(hostname)) is result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4v6")}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v6-only")}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("no-ip")}, False),
    ],
)
def test_is_ipv6_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert (AddressFamily.IPv6 in config_cache.address_family(hostname)) is result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4v6")}, True),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v6-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("no-ip")}, False),
    ],
)
def test_is_ipv4v6_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert (config_cache.address_family(hostname) is AddressFamily.DUAL_STACK) is result


def test_ip_address_of(monkeypatch: MonkeyPatch) -> None:
    _FALLBACK_ADDRESS_IPV4: Final = "0.0.0.0"
    _FALLBACK_ADDRESS_IPV6: Final = "::"
    localhost = HostName("localhost")
    no_ip = HostName("no_ip")
    dual_stack = HostName("dual_stack")
    cluster = HostName("cluster")
    bad_host = HostName("bad_host")
    undiscoverable = HostName("undiscoverable")

    ts = Scenario()
    ts.add_host(localhost)
    ts.add_host(HostName(undiscoverable))
    ts.add_host(HostName(no_ip), {TagGroupID("address_family"): TagID("no-ip")})
    ts.add_host(HostName(dual_stack), {TagGroupID("address_family"): TagID("ip-v4v6")})
    ts.add_cluster(HostName(cluster))
    config_cache = ts.apply(monkeypatch)
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port, family=None, *args, **kwargs: {
            (localhost, socket.AF_INET): [(family, None, None, None, ("127.0.0.1", 0))],
            (localhost, socket.AF_INET6): [(family, None, None, None, ("::1", 0))],
        }[(host, family)],
    )

    assert config_cache.default_address_family(localhost) is socket.AF_INET
    assert config_cache.address_family(localhost) is AddressFamily.IPv4
    assert ip_address_of(config_cache, localhost, socket.AF_INET) == "127.0.0.1"
    assert ip_address_of(config_cache, localhost, socket.AF_INET6) == "::1"

    assert config_cache.default_address_family(no_ip) is socket.AF_INET
    assert config_cache.address_family(no_ip) is AddressFamily.NO_IP
    assert ip_address_of(config_cache, no_ip, socket.AF_INET) is None
    assert ip_address_of(config_cache, no_ip, socket.AF_INET6) is None

    assert config_cache.default_address_family(dual_stack) is socket.AF_INET
    assert config_cache.address_family(dual_stack) is AddressFamily.DUAL_STACK
    assert ip_address_of(config_cache, dual_stack, socket.AF_INET) == _FALLBACK_ADDRESS_IPV4
    assert ip_address_of(config_cache, dual_stack, socket.AF_INET6) == _FALLBACK_ADDRESS_IPV6

    assert config_cache.default_address_family(cluster) is socket.AF_INET
    assert config_cache.address_family(cluster) is AddressFamily.IPv4  # That's strange
    assert ip_address_of(config_cache, cluster, socket.AF_INET) == ""
    assert ip_address_of(config_cache, cluster, socket.AF_INET6) == ""

    assert config_cache.default_address_family(bad_host) is socket.AF_INET
    assert config_cache.address_family(bad_host) is AddressFamily.IPv4  # That's strange
    assert ip_address_of(config_cache, bad_host, socket.AF_INET) == _FALLBACK_ADDRESS_IPV4
    assert ip_address_of(config_cache, bad_host, socket.AF_INET6) == _FALLBACK_ADDRESS_IPV6

    assert config_cache.default_address_family(undiscoverable) is socket.AF_INET
    assert config_cache.address_family(undiscoverable) is AddressFamily.IPv4  # That's strange
    assert ip_address_of(config_cache, undiscoverable, socket.AF_INET) == _FALLBACK_ADDRESS_IPV4
    assert ip_address_of(config_cache, undiscoverable, socket.AF_INET6) == _FALLBACK_ADDRESS_IPV6


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {TagGroupID("piggyback"): TagID("piggyback")}, True),
        (HostName("testhost"), {TagGroupID("piggyback"): TagID("no-piggyback")}, False),
    ],
)
def test_is_piggyback_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_piggyback_host(hostname) == result


@pytest.mark.parametrize(
    "with_data,result",
    [
        (True, True),
        (False, False),
    ],
)
@pytest.mark.parametrize(
    "hostname, tags",
    [
        (HostName("testhost"), {}),
        (HostName("testhost"), {TagGroupID("piggyback"): TagID("auto-piggyback")}),
    ],
)
def test_is_piggyback_host_auto(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    tags: dict[TagGroupID, TagID],
    with_data: bool,
    result: bool,
) -> None:
    monkeypatch.setattr(piggyback, "has_piggyback_raw_data", lambda *args, **kw: with_data)
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_piggyback_host(hostname) == result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4v6")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v6-only")}, False),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("no-ip")}, True),
    ],
)
def test_is_no_ip_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    config_cache = ts.apply(monkeypatch)
    assert (config_cache.address_family(hostname) is AddressFamily.NO_IP) is result


@pytest.mark.parametrize(
    "hostname, tags, result, ruleset",
    [
        (HostName("testhost"), {}, False, []),
        (
            HostName("testhost"),
            {TagGroupID("address_family"): TagID("ip-v4-only")},
            False,
            [{"id": "01", "condition": {}, "value": "ipv6"}],
        ),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v4v6")}, False, []),
        (
            HostName("testhost"),
            {TagGroupID("address_family"): TagID("ip-v4v6")},
            True,
            [{"id": "02", "condition": {}, "value": "ipv6"}],
        ),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("ip-v6-only")}, True, []),
        (
            HostName("testhost"),
            {TagGroupID("address_family"): TagID("ip-v6-only")},
            True,
            [{"id": "03", "condition": {}, "value": "ipv4"}],
        ),
        (
            HostName("testhost"),
            {TagGroupID("address_family"): TagID("ip-v6-only")},
            True,
            [{"id": "04", "condition": {}, "value": "ipv6"}],
        ),
        (HostName("testhost"), {TagGroupID("address_family"): TagID("no-ip")}, False, []),
    ],
)
def test_is_ipv6_primary_host(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    tags: dict[TagGroupID, TagID],
    result: bool,
    ruleset: list,
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    ts.set_ruleset("primary_address_family", ruleset)
    config_cache = ts.apply(monkeypatch)
    assert (config_cache.default_address_family(hostname) is socket.AF_INET6) is result


@pytest.mark.parametrize(
    "result,attrs",
    [
        ("127.0.1.1", {}),
        ("127.0.1.1", {"management_address": ""}),
        ("127.0.0.1", {"management_address": "127.0.0.1"}),
        ("lolo", {"management_address": "lolo"}),
    ],
)
def test_host_config_management_address(
    monkeypatch: MonkeyPatch, attrs: dict[str, str], result: str
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("ipaddresses", {hostname: "127.0.1.1"})
    ts.set_option("host_attributes", {hostname: attrs})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.management_address(hostname) == result


def _management_config_ruleset() -> Sequence[RuleSpec[object]]:
    return [
        {"id": "01", "condition": {}, "value": ("snmp", "eee")},
        {"id": "02", "condition": {}, "value": ("ipmi", {"username": "eee", "password": "eee"})},
    ]


@pytest.mark.parametrize(
    "expected_result,protocol,credentials,ruleset",
    [
        ("public", "snmp", None, []),
        ({}, "ipmi", None, []),
        ("aaa", "snmp", "aaa", []),
        (
            {"username": "aaa", "password": "aaa"},
            "ipmi",
            {"username": "aaa", "password": "aaa"},
            [],
        ),
        ("eee", "snmp", None, _management_config_ruleset()),
        ({"username": "eee", "password": "eee"}, "ipmi", None, _management_config_ruleset()),
        ("aaa", "snmp", "aaa", _management_config_ruleset()),
        (
            {"username": "aaa", "password": "aaa"},
            "ipmi",
            {"username": "aaa", "password": "aaa"},
            _management_config_ruleset(),
        ),
    ],
)
def test_host_config_management_credentials(
    monkeypatch: MonkeyPatch,
    protocol: Literal["snmp", "ipmi"],
    credentials: dict[str, str] | None,
    expected_result: str | dict[str, str] | None,
    ruleset: Sequence[RuleSpec[object]],
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("host_attributes", {hostname: {"management_address": "127.0.0.1"}})
    ts.set_option("management_protocol", {hostname: protocol})

    if credentials is not None:
        if protocol == "snmp":
            ts.set_option("management_snmp_credentials", {hostname: credentials})
        elif protocol == "ipmi":
            ts.set_option("management_ipmi_credentials", {hostname: credentials})
        else:
            raise NotImplementedError()

    ts.set_ruleset("management_board_config", ruleset)

    config_cache = ts.apply(monkeypatch)
    assert config_cache.management_credentials(hostname, protocol) == expected_result


@pytest.mark.parametrize(
    "attrs,result",
    [
        ({}, ([], [])),
        (
            {
                "additional_ipv4addresses": ["10.10.10.10"],
                "additional_ipv6addresses": ["::3"],
            },
            (["10.10.10.10"], ["::3"]),
        ),
    ],
)
def test_host_config_additional_ipaddresses(
    monkeypatch: MonkeyPatch, attrs: dict[str, list[str]], result: tuple[list[str], list[str]]
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("ipaddresses", {hostname: "127.0.1.1"})
    ts.set_option("host_attributes", {hostname: attrs})
    config_cache = ts.apply(monkeypatch)

    assert config_cache.additional_ipaddresses(hostname) == result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, True),
        (HostName("testhost"), {TagGroupID("agent"): TagID("cmk-agent")}, True),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")},
            True,
        ),
        (HostName("testhost"), {TagGroupID("agent"): TagID("no-agent")}, False),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("no-agent"), TagGroupID("snmp_ds"): TagID("no-snmp")},
            False,
        ),
    ],
)
def test_is_tcp_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_tcp_host(hostname) == result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("cmk-agent")}, False),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v1")},
            False,
        ),
        (HostName("testhost"), {TagGroupID("snmp_ds"): TagID("snmp-v1")}, False),
        (
            HostName("testhost"),
            {
                TagGroupID("agent"): TagID("no-agent"),
                TagGroupID("snmp_ds"): TagID("no-snmp"),
                TagGroupID("piggyback"): TagID("no-piggyback"),
            },
            True,
        ),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("no-agent"), TagGroupID("snmp_ds"): TagID("no-snmp")},
            True,
        ),
        (HostName("testhost"), {TagGroupID("agent"): TagID("no-agent")}, True),
    ],
)
def test_is_ping_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_ping_host(hostname) is result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("cmk-agent")}, False),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v1")},
            True,
        ),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")},
            True,
        ),
        (
            HostName("testhost"),
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("no-snmp")},
            False,
        ),
    ],
)
def test_is_snmp_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_snmp_host(hostname) is result


def test_is_not_usewalk_host(monkeypatch: MonkeyPatch) -> None:
    hostname = HostName("xyz")
    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_snmp_backend(hostname) is not SNMPBackendEnum.STORED_WALK


def test_is_usewalk_host(monkeypatch: MonkeyPatch) -> None:
    hostname = HostName("xyz")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "usewalk_hosts",
        [
            {
                "id": "01",
                "condition": {"host_name": [hostname]},
                "value": True,
            },
        ],
    )

    config_cache = ts.apply(monkeypatch)
    assert config_cache.get_snmp_backend(hostname) is SNMPBackendEnum.STORED_WALK


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("all-agents")}, True),
        (HostName("testhost"), {TagGroupID("agent"): TagID("special-agents")}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("no-agent")}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("cmk-agent")}, False),
    ],
)
def test_is_all_agents_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_all_agents_host(hostname) is result


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("all-agents")}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("special-agents")}, True),
        (HostName("testhost"), {TagGroupID("agent"): TagID("no-agent")}, False),
        (HostName("testhost"), {TagGroupID("agent"): TagID("cmk-agent")}, False),
    ],
)
def test_is_all_special_agents_host(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_all_special_agents_host(hostname) is result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), 6556),
        (HostName("testhost2"), 1337),
    ],
)
def test_agent_port(monkeypatch: MonkeyPatch, hostname: HostName, result: int) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "agent_ports",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": 1337,
                "options": {},
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache._agent_port(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), 5.0),
        (HostName("testhost2"), 12.0),
    ],
)
def test_tcp_connect_timeout(monkeypatch: MonkeyPatch, hostname: HostName, result: float) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "tcp_connect_timeouts",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": 12.0,
                "options": {},
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache._tcp_connect_timeout(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), TCPEncryptionHandling.ANY_AND_PLAIN),
        (HostName("testhost2"), TCPEncryptionHandling.TLS_ENCRYPTED_ONLY),
    ],
)
def test_encryption_handling(
    monkeypatch: MonkeyPatch, hostname: HostName, result: TCPEncryptionHandling
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "encryption_handling",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {"accept": "tls_encrypted_only"},
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache._encryption_handling(hostname) is result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), "my-super-secret-psk"),
    ],
)
def test_symmetric_agent_encryption(
    monkeypatch: MonkeyPatch, hostname: HostName, result: str | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "agent_encryption",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "my-super-secret-psk",
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache._symmetric_agent_encryption(hostname) is result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), cmk_version.__version__),
    ],
)
def test_agent_target_version(
    monkeypatch: MonkeyPatch, hostname: HostName, result: str | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_agent_target_versions",
        [
            {
                "id": "01",
                "condition": {"host_name": ["testhost2"]},
                "value": "site",
            }
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.agent_target_version(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (
            HostName("testhost2"),
            [
                ("abc", {"param1": 1}),
                ("xyz", {"param2": 1}),
            ],
        ),
    ],
)
def test_special_agents(monkeypatch: MonkeyPatch, hostname: HostName, result: list[tuple]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "special_agents",
        {
            "abc": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {"param1": 1},
                }
            ],
            "xyz": [
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {"param2": 1},
                }
            ],
        },
    )
    assert ts.apply(monkeypatch).special_agents(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), ["127.0.0.1"]),
    ],
)
def test_only_from(monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "agent_config",
        {
            "only_from": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["127.0.0.1"],
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["127.0.0.2"],
                },
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.only_from(hostname) == result


@pytest.mark.parametrize(
    "hostname, core_name, result",
    [
        (HostName("testhost1"), "cmc", None),
        (HostName("testhost2"), "cmc", "command1"),
        (HostName("testhost3"), "cmc", "smart"),
        (HostName("testhost3"), "nagios", "ping"),
    ],
)
def test_explicit_check_command(
    monkeypatch: MonkeyPatch, hostname: HostName, core_name: str, result: str | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("monitoring_core", core_name)
    ts.set_option(
        "host_check_commands",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "command1",
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "command2",
            },
            {
                "id": "03",
                "condition": {"host_name": [HostName("testhost3")]},
                "value": "smart",
            },
        ],
    )
    assert ts.apply(monkeypatch).explicit_check_command(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (HostName("testhost2"), {"ding": 1, "dong": 1}),
    ],
)
def test_ping_levels(monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, int]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "ping_levels",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {"ding": 1},
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {"ding": 3},
            },
            {
                "id": "03",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {"dong": 1},
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.ping_levels(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (HostName("testhost2"), ["icon1", "icon2"]),
    ],
)
def test_icons_and_actions(monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_icons_and_actions",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "icon1",
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "icon1",
            },
            {
                "id": "03",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "icon2",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.icons_and_actions(hostname)) == sorted(result)


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (HostName("testhost2"), {"_CUSTOM": ["value1"], "dingdong": ["value1"]}),
    ],
)
def test_host_config_extra_host_attributes(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, list[str]]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "extra_host_conf",
        {
            "dingdong": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["value1"],
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["value2"],
                },
            ],
            "_custom": [
                {
                    "id": "03",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["value1"],
                },
                {
                    "id": "04",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ["value2"],
                },
            ],
        },
    )
    assert ts.apply(monkeypatch).extra_host_attributes(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (
            HostName("testhost2"),
            {
                "value1": 1,
                "value2": 2,
            },
        ),
    ],
)
def test_host_config_inventory_parameters(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, int]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "inv_parameters",
        {
            "if": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {"value1": 1},
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {"value2": 2},
                },
            ],
        },
    )
    plugin = InventoryPlugin(
        sections=(), function=lambda *args, **kw: (), ruleset_name=RuleSetName("if")
    )
    assert ts.apply(monkeypatch).inventory_parameters(hostname, plugin) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (
            HostName("testhost1"),
            DiscoveryCheckParameters(
                commandline_only=True,
                check_interval=0,
                severity_new_services=1,
                severity_vanished_services=0,
                severity_new_host_labels=1,
                rediscovery={},
            ),
        ),
        (
            HostName("testhost2"),
            DiscoveryCheckParameters(
                commandline_only=False,
                check_interval=1,
                severity_new_services=1,
                severity_vanished_services=0,
                severity_new_host_labels=1,
                rediscovery={},
            ),
        ),
    ],
)
def test_discovery_check_parameters(
    monkeypatch: MonkeyPatch, hostname: HostName, result: DiscoveryCheckParameters
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "periodic_discovery",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "check_interval": 1,
                    "severity_unmonitored": 1,
                    "severity_vanished": 0,
                    "severity_new_host_label": 1,
                },
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "check_interval": 2,
                    "severity_unmonitored": 1,
                    "severity_vanished": 0,
                    "severity_new_host_label": 1,
                },
            },
        ],
    )
    assert ts.apply(monkeypatch).discovery_check_parameters(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (
            HostName("testhost2"),
            {
                "value1": 1,
                "value2": 2,
            },
        ),
    ],
)
def test_notification_plugin_parameters(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, int]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "notification_parameters",
        {
            "mail": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {
                        "value1": 1,
                    },
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {
                        "value1": 2,
                        "value2": 2,
                    },
                },
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.notification_plugin_parameters(hostname, "mail") == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (
            HostName("testhost2"),
            [
                (
                    "abc",
                    [{"param1": 1}, {"param2": 2}],
                ),
                (
                    "xyz",
                    [
                        {"param2": 1},
                    ],
                ),
            ],
        ),
    ],
)
def test_host_config_active_checks(
    monkeypatch: MonkeyPatch, hostname: HostName, result: list[tuple]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "active_checks",
        {
            "abc": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {
                        "param1": 1,
                    },
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {
                        "param2": 2,
                    },
                },
            ],
            "xyz": [
                {
                    "id": "03",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": {
                        "param2": 1,
                    },
                },
            ],
        },
    )
    assert ts.apply(monkeypatch).active_checks(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (HostName("testhost2"), [{"param1": 1}, {"param2": 2}]),
    ],
)
def test_host_config_custom_checks(
    monkeypatch: MonkeyPatch, hostname: HostName, result: list[dict[str, int]]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "custom_checks",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "param1": 1,
                },
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "param2": 2,
                },
            },
        ],
    )
    assert ts.apply(monkeypatch).custom_checks(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (
            HostName("testhost2"),
            {
                ServiceID(CheckPluginName("checktype1"), "item1"): (
                    "checkgroup",
                    ConfiguredService(
                        check_plugin_name=CheckPluginName("checktype1"),
                        item="item1",
                        description="Test fake checktype1 / item1",
                        parameters=TimespecificParameters(
                            (
                                TimespecificParameterSet({"param1": 1}, ()),
                                TimespecificParameterSet({}, ()),
                                TimespecificParameterSet({}, ()),
                            )
                        ),
                        discovered_parameters={},
                        service_labels={},
                        is_enforced=True,
                    ),
                ),
                ServiceID(CheckPluginName("checktype2"), "item2"): (
                    "checkgroup",
                    ConfiguredService(
                        check_plugin_name=CheckPluginName("checktype2"),
                        item="item2",
                        description="Test fake checktype2 / item2",
                        parameters=TimespecificParameters(
                            (
                                TimespecificParameterSet({"param2": 2}, ()),
                                TimespecificParameterSet({}, ()),
                                TimespecificParameterSet({}, ()),
                            )
                        ),
                        discovered_parameters={},
                        service_labels={},
                        is_enforced=True,
                    ),
                ),
            },
        ),
    ],
)
def test_host_config_static_checks(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    result: Mapping[ServiceID, tuple[str, ConfiguredService]],
) -> None:
    def make_plugin(name: CheckPluginName) -> CheckPluginAPI:
        return CheckPluginAPI(
            name=name,
            sections=[],
            service_name="Test fake %s / %%s" % name,
            discovery_function=lambda *args, **kw: (),
            discovery_default_parameters=None,
            discovery_ruleset_name=None,
            discovery_ruleset_type="all",
            check_function=lambda *args, **kw: (),
            check_default_parameters=None,
            check_ruleset_name=None,
            cluster_check_function=None,
            location=None,
        )

    monkeypatch.setattr(agent_based_register, "get_check_plugin", make_plugin)

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "static_checks",
        {
            "checkgroup": [
                {
                    "id": "01",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ("checktype1", "item1", {"param1": 1}),
                },
                {
                    "id": "02",
                    "condition": {"host_name": [HostName("testhost2")]},
                    "value": ("checktype2", "item2", {"param2": 2}),
                },
            ],
        },
    )
    assert ts.apply(monkeypatch).enforced_services_table(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), ["check_mk"]),
        (HostName("testhost2"), ["dingdong"]),
    ],
)
def test_hostgroups(monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_groups",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": "dingdong",
            },
        ],
    )
    assert ts.apply(monkeypatch).hostgroups(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        # No rule matches for this host
        (HostName("testhost1"), ["check-mk-notify"]),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        (HostName("testhost2"), ["abc", "dingdong", "check-mk-notify"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        (HostName("testhost3"), ["abc", "dingdong", "haha", "check-mk-notify"]),
    ],
)
def test_contactgroups(monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_contactgroups",
        [
            # Seems both, a list of groups and a group name is allowed. We should clean
            # this up to be always a list of groups in the future...
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2"), HostName("testhost3")]},
                "value": "dingdong",
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2"), HostName("testhost3")]},
                "value": ["abc"],
            },
            {
                "id": "03",
                "condition": {"host_name": [HostName("testhost2"), HostName("testhost3")]},
                "value": ["xyz"],
            },
            {
                "id": "04",
                "condition": {"host_name": [HostName("testhost3")]},
                "value": "haha",
            },
        ],
    )
    assert sorted(ts.apply(monkeypatch).contactgroups(hostname)) == sorted(result)


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (HostName("testhost2"), {"connection": 1}),
    ],
)
def test_config_cache_exit_code_spec_overall(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, int]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "overall": {"connection": 1},
                    "individual": {"snmp": {"connection": 4}},
                },
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.exit_code_spec(hostname) == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (HostName("testhost2"), {"connection": 4}),
    ],
)
def test_config_cache_exit_code_spec_individual(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, int]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": {
                    "overall": {"connection": 1},
                    "individual": {"snmp": {"connection": 4}},
                },
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.exit_code_spec(hostname, data_source_id="snmp") == result


@pytest.mark.parametrize(
    "ruleset",
    [
        {
            "connection": 2,
            "restricted_address_mismatch": 2,
        },
        {
            "overall": {
                "connection": 2,
            },
            "restricted_address_mismatch": 2,
        },
        {
            "individual": {
                "snmp": {
                    "connection": 2,
                }
            },
            "restricted_address_mismatch": 2,
        },
        {
            "overall": {
                "connection": 1000,
            },
            "individual": {
                "snmp": {
                    "connection": 2,
                }
            },
            "restricted_address_mismatch": 2,
        },
    ],
)
def test_config_cache_exit_code_spec(monkeypatch: MonkeyPatch, ruleset: dict[str, Any]) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_mk_exit_status",
        [
            {
                "id": "01",
                "condition": {"host_name": [hostname]},
                "value": ruleset,
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)

    exit_code_spec = config_cache.exit_code_spec(hostname)
    assert "restricted_address_mismatch" in exit_code_spec
    assert exit_code_spec["restricted_address_mismatch"] == 2

    result = {
        "connection": 2,
        "restricted_address_mismatch": 2,
    }
    snmp_exit_code_spec = config_cache.exit_code_spec(hostname, data_source_id="snmp")
    assert snmp_exit_code_spec == result


@pytest.mark.parametrize(
    "hostname, version, result",
    [
        (HostName("testhost1"), 2, None),
        (HostName("testhost2"), 2, "bla"),
        (HostName("testhost2"), 3, ("noAuthNoPriv", "v3")),
        (HostName("testhost3"), 2, "bla"),
        (HostName("testhost3"), 3, None),
        (HostName("testhost4"), 2, None),
        (HostName("testhost4"), 3, ("noAuthNoPriv", "v3")),
    ],
)
def test_config_cache_snmp_credentials_of_version(
    monkeypatch: MonkeyPatch,
    hostname: HostName,
    version: int,
    result: None | str | tuple[str, str],
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "snmp_communities",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2"), HostName("testhost3")]},
                "value": "bla",
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2"), HostName("testhost4")]},
                "value": ("noAuthNoPriv", "v3"),
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.snmp_credentials_of_version(hostname, version) == result


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname, section_name, result",
    [
        (HostName("testhost1"), "uptime", None),
        (HostName("testhost2"), "uptime", None),
        (HostName("testhost1"), "snmp_uptime", None),
        (HostName("testhost2"), "snmp_uptime", 4),
    ],
)
def test_snmp_check_interval(
    monkeypatch: MonkeyPatch, hostname: HostName, section_name: str, result: int | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "snmp_check_interval",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": ("snmp_uptime", 4),
            },
        ],
    )
    assert ts.apply(monkeypatch).snmp_fetch_interval(hostname, SectionName(section_name)) == (
        60 * result if result else None
    )


def test_http_proxies() -> None:
    assert not config.http_proxies


@pytest.fixture(name="service_list")
def _service_list() -> list[ConfiguredService]:
    return [
        ConfiguredService(
            check_plugin_name=CheckPluginName("plugin_%s" % d),
            item="item",
            description="description %s" % d,
            parameters=TimespecificParameters(),
            discovered_parameters={},
            service_labels={},
            is_enforced=False,
        )
        for d in "FDACEB"
    ]


def test_get_sorted_check_table_no_cmc(
    monkeypatch: MonkeyPatch, service_list: list[ConfiguredService]
) -> None:
    host_name = HostName("horst")
    ts = Scenario()
    ts.add_host(host_name)
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(config_cache, "_sorted_services", lambda *args: service_list)
    monkeypatch.setattr(
        config,
        "service_depends_on",
        lambda _cc, _hn, descr: {
            "description A": ["description C"],
            "description B": ["description D"],
            "description D": ["description A", "description F"],
        }.get(descr, []),
    )

    services = config_cache.configured_services(host_name)
    assert [s.description for s in services] == [
        "description F",  #
        "description C",  # no deps => input order maintained
        "description E",  #
        "description A",
        "description D",
        "description B",
    ]


def test_resolve_service_dependencies_cyclic(
    monkeypatch: MonkeyPatch, service_list: list[ConfiguredService]
) -> None:
    host_name = HostName("MyHost")
    ts = Scenario()
    ts.add_host(host_name)
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(config, "is_cmc", lambda: False)
    monkeypatch.setattr(config_cache, "_sorted_services", lambda *args: service_list)
    monkeypatch.setattr(
        config,
        "service_depends_on",
        lambda _cc, _hn, descr: {
            "description A": ["description B"],
            "description B": ["description D"],
            "description D": ["description A"],
        }.get(descr, []),
    )

    with pytest.raises(
        MKGeneralException,
        match=re.escape(
            "Cyclic service dependency of host MyHost:"
            " 'description D' (plugin_D / item),"
            " 'description A' (plugin_A / item),"
            " 'description B' (plugin_B / item)"
        ),
    ):
        config_cache.configured_services(HostName("MyHost"))


def test_service_depends_on_unknown_host(monkeypatch: MonkeyPatch) -> None:
    config_cache = Scenario().apply(monkeypatch)
    assert not config.service_depends_on(config_cache, HostName("test-host"), "svc")


def test_service_depends_on(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    ts = Scenario()
    ts.add_host(test_host)
    ts.set_option(
        "service_dependencies",
        [
            ("dep1", [], config.ALL_HOSTS, ["svc1"], {}),
            ("dep2-%s", [], config.ALL_HOSTS, ["svc1-(.*)"], {}),
            ("dep-disabled", [], config.ALL_HOSTS, ["svc1"], {"disabled": True}),
        ],
    )
    config_cache = ts.apply(monkeypatch)

    assert not config.service_depends_on(config_cache, test_host, "svc2")
    assert config.service_depends_on(config_cache, test_host, "svc1") == ["dep1"]
    assert config.service_depends_on(config_cache, test_host, "svc1-abc") == ["dep1", "dep2-abc"]


@pytest.fixture(name="cluster_config")
def cluster_config_fixture(monkeypatch: MonkeyPatch) -> ConfigCache:
    ts = Scenario()
    ts.add_host(HostName("node1"))
    ts.add_host(HostName("host1"))
    ts.add_cluster(HostName("cluster1"), nodes=[HostName("node1")])
    return ts.apply(monkeypatch)


def test_config_cache_is_cluster(cluster_config: ConfigCache) -> None:
    assert HostName("node1") not in cluster_config.hosts_config.clusters
    assert HostName("host1") not in cluster_config.hosts_config.clusters
    assert HostName("cluster1") in cluster_config.hosts_config.clusters


def test_config_cache_clusters_of(cluster_config: ConfigCache) -> None:
    assert cluster_config.clusters_of(HostName("node1")) == ["cluster1"]
    assert cluster_config.clusters_of(HostName("host1")) == []
    assert cluster_config.clusters_of(HostName("cluster1")) == []


def test_config_cache_nodes_of(cluster_config: ConfigCache) -> None:
    assert cluster_config.nodes_of(HostName("node1")) is None
    assert cluster_config.nodes_of(HostName("host1")) is None
    assert cluster_config.nodes_of(HostName("cluster1")) == ["node1"]


def test_host_config_parents(cluster_config: ConfigCache) -> None:
    assert cluster_config.parents(HostName("node1")) == []
    assert cluster_config.parents(HostName("host1")) == []
    # TODO: Move cluster/node parent handling to HostConfig
    # assert cluster_config.make_cee_host_config("cluster1").parents == ["node1"]
    assert cluster_config.parents(HostName("cluster1")) == []


def test_config_cache_tag_list_of_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts.add_host(test_host, tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(xyz_host)

    config_cache = ts.apply(monkeypatch)
    assert set(config_cache.tag_list(xyz_host)) == {
        TagID("/wato/"),
        TagID("lan"),
        TagID("ip-v4"),
        TagID("checkmk-agent"),
        TagID("cmk-agent"),
        TagID("no-snmp"),
        TagID("tcp"),
        TagID("auto-piggyback"),
        TagID("ip-v4-only"),
        TagID("site:unit"),
        TagID("prod"),
    }


def test_config_cache_tag_list_of_host_not_existing(monkeypatch: MonkeyPatch) -> None:
    config_cache = Scenario().apply(monkeypatch)
    assert set(config_cache.tag_list(HostName("not-existing"))) == {
        TagID("/"),
        TagID("lan"),
        TagID("cmk-agent"),
        TagID("no-snmp"),
        TagID("auto-piggyback"),
        TagID("ip-v4-only"),
        TagID("site:NO_SITE"),
        TagID("prod"),
    }


def test_host_tags_default() -> None:
    assert isinstance(config.host_tags, dict)


def test_host_tags_of_host(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts = Scenario()
    ts.add_host(test_host, tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(xyz_host)

    config_cache = ts.apply(monkeypatch)
    assert config_cache.tags(xyz_host) == {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
        "tcp": "tcp",
        "checkmk-agent": "checkmk-agent",
    }
    assert config_cache.tags(test_host) == {
        "address_family": "ip-v4-only",
        "agent": "no-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
    }


def test_service_tag_rules_default() -> None:
    assert isinstance(config.service_tag_rules, list)


def test_tags_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.add_host(test_host, tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(xyz_host)
    ts.set_ruleset(
        "service_tag_rules",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_tags": {TagGroupID("agent"): TagID("no-agent")},
                },
                "value": [("criticality", "prod")],
            }
        ],
    )

    config_cache = ts.apply(monkeypatch)

    assert config_cache.tags(xyz_host) == {
        "address_family": "ip-v4-only",
        "agent": "cmk-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
        "tcp": "tcp",
        "checkmk-agent": "checkmk-agent",
    }
    assert config_cache.tags_of_service(xyz_host, "CPU load") == {}

    assert config_cache.tags(test_host) == {
        "address_family": "ip-v4-only",
        "agent": "no-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
    }
    assert config_cache.tags_of_service(test_host, "CPU load") == {"criticality": "prod"}


def test_host_label_rules_default() -> None:
    assert isinstance(config.host_label_rules, list)


def test_labels(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.set_ruleset(
        "host_label_rules",
        [
            {
                "id": "01",
                "condition": {"host_tags": {TagGroupID("agent"): TagID("no-agent")}},
                "value": {"from-rule": "rule1"},
            },
            {
                "id": "02",
                "condition": {"host_tags": {TagGroupID("agent"): TagID("no-agent")}},
                "value": {"from-rule2": "rule2"},
            },
        ],
    )

    ts.add_host(
        test_host, tags={TagGroupID("agent"): TagID("no-agent")}, labels={"explicit": "ding"}
    )
    ts.add_host(xyz_host)

    config_cache = ts.apply(monkeypatch)
    assert config_cache.labels(xyz_host) == {"cmk/site": "NO_SITE"}
    assert config_cache.labels(test_host) == {
        "cmk/site": "NO_SITE",
        "explicit": "ding",
        "from-rule": "rule1",
        "from-rule2": "rule2",
    }
    assert config_cache.label_sources(test_host) == {
        "cmk/site": "discovered",
        "explicit": "explicit",
        "from-rule": "ruleset",
        "from-rule2": "ruleset",
    }


def test_host_labels_of_host_discovered_labels(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    test_host = HostName("test-host")
    ts = Scenario()
    ts.add_host(test_host)

    monkeypatch.setattr(cmk.utils.paths, "discovered_host_labels_dir", tmp_path)
    host_file = (tmp_path / test_host).with_suffix(".mk")
    with host_file.open(mode="w", encoding="utf-8") as f:
        f.write(repr({"äzzzz": {"value": "eeeeez", "plugin_name": "ding123"}}) + "\n")

    config_cache = ts.apply(monkeypatch)
    assert config_cache.labels(test_host) == {
        "cmk/site": "NO_SITE",
        "äzzzz": "eeeeez",
    }
    assert config_cache.label_sources(test_host) == {
        "cmk/site": "discovered",
        "äzzzz": "discovered",
    }


def test_service_label_rules_default() -> None:
    assert isinstance(config.service_label_rules, list)


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {"check_interval": 1.0}),
        (
            HostName("testhost2"),
            {
                "_CUSTOM": ["value1"],
                "dingdong": ["value1"],
                "check_interval": 10.0,
            },
        ),
    ],
)
def test_config_cache_extra_attributes_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, Any]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option(
        "extra_service_conf",
        {
            "check_interval": [
                {
                    "id": "01",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": [HostName("testhost2")],
                    },
                    "value": "10",
                },
            ],
            "dingdong": [
                {
                    "id": "02",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": [HostName("testhost2")],
                    },
                    "value": ["value1"],
                },
                {
                    "id": "03",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": [HostName("testhost2")],
                    },
                    "value": ["value2"],
                },
            ],
            "_custom": [
                {
                    "id": "04",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": [HostName("testhost2")],
                    },
                    "value": ["value1"],
                },
                {
                    "id": "05",
                    "condition": {
                        "service_description": [{"$regex": "CPU load$"}],
                        "host_name": [HostName("testhost2")],
                    },
                    "value": ["value2"],
                },
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.extra_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.usefixtures("fix_register")
@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (HostName("testhost2"), ["icon1", "icon2"]),
    ],
)
def test_config_cache_icons_and_actions(
    monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_icons_and_actions",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "icon1",
            },
            {
                "id": "02",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "icon1",
            },
            {
                "id": "03",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "icon2",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(
        config_cache.icons_and_actions_of_service(
            hostname,
            "CPU load",
            CheckPluginName("ps"),
            {},
        )
    ) == sorted(result)


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (HostName("testhost2"), ["dingdong"]),
    ],
)
def test_config_cache_servicegroups_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_groups",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "dingdong",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.servicegroups_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        # No rule matches for this host
        (HostName("testhost1"), ["check-mk-notify"]),
        # Take the group from the ruleset (dingdong) and the definition from the nearest folder in
        # the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        (HostName("testhost2"), ["abc", "dingdong", "check-mk-notify"]),
        # Take the group from all rulesets (dingdong, haha) and the definition from the nearest
        # folder in the hierarchy (abc). Don't apply the definition from the parent folder (xyz).
        (HostName("testhost3"), ["abc", "dingdong", "haha", "check-mk-notify"]),
    ],
)
def test_config_cache_contactgroups_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: list[str]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_contactgroups",
        [
            # Just like host_contactgroups, a list of groups and a group name is
            # allowed. We should clean this up to be always a list of groups in the
            # future...
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2"), HostName("testhost3")],
                },
                "value": "dingdong",
            },
            {
                "id": "02",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2"), HostName("testhost3")],
                },
                "value": ["abc"],
            },
            {
                "id": "03",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2"), HostName("testhost3")],
                },
                "value": ["xyz"],
            },
            {
                "id": "04",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost3")],
                },
                "value": "haha",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert sorted(config_cache.contactgroups_of_service(hostname, "CPU load")) == sorted(result)


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), "24X7"),
        (HostName("testhost2"), "workhours"),
    ],
)
def test_config_cache_passive_check_period_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: str
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_periods",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "workhours",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.passive_check_period_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (
            HostName("testhost2"),
            {
                "ATTR1": "value1",
                "ATTR2": "value2",
            },
        ),
    ],
)
def test_config_cache_custom_attributes_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: dict[str, str]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "custom_service_attributes",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": [
                    ("ATTR1", "value1"),
                    ("ATTR2", "value2"),
                ],
            },
            {
                "id": "02",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": [
                    ("ATTR1", "value1"),
                ],
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.custom_attributes_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), 10),
    ],
)
def test_config_cache_service_level_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: int | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "service_service_levels",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": 10,
            },
            {
                "id": "02",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": 2,
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.service_level_of_service(hostname, "CPU load") == result


@pytest.mark.parametrize(
    "hostname,result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), None),
        (HostName("testhost3"), "xyz"),
    ],
)
def test_config_cache_check_period_of_service(
    monkeypatch: MonkeyPatch, hostname: HostName, result: str | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "check_periods",
        [
            {
                "id": "01",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost2")],
                },
                "value": "24X7",
            },
            {
                "id": "02",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost3")],
                },
                "value": "xyz",
            },
            {
                "id": "03",
                "condition": {
                    "service_description": [{"$regex": "CPU load$"}],
                    "host_name": [HostName("testhost3")],
                },
                "value": "zzz",
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.check_period_of_service(hostname, "CPU load") == result


def test_config_cache_max_cachefile_age_no_cluster(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    xyz_host = HostName("xyz")
    ts.add_host(xyz_host)
    ts.apply(monkeypatch)

    config_cache = ts.config_cache
    assert xyz_host not in config_cache.hosts_config.clusters
    assert (
        config_cache.max_cachefile_age(xyz_host).get(Mode.CHECKING)
        == config.check_max_cachefile_age
    )
    assert (
        config_cache.max_cachefile_age(xyz_host).get(Mode.CHECKING)
        != config.cluster_max_cachefile_age
    )


def test_config_cache_max_cachefile_age_cluster(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    clu = HostName("clu")
    ts.add_cluster(clu)
    ts.apply(monkeypatch)

    config_cache = ts.config_cache
    assert clu in config_cache.hosts_config.clusters
    assert config_cache.max_cachefile_age(clu).get(Mode.CHECKING) != config.check_max_cachefile_age
    assert (
        config_cache.max_cachefile_age(clu).get(Mode.CHECKING) == config.cluster_max_cachefile_age
    )


@pytest.mark.parametrize(
    "use_new_descr,result",
    [
        (True, "Check_MK Discovery"),
        (False, "Check_MK inventory"),
    ],
)
def test_config_cache_service_discovery_name(
    monkeypatch: MonkeyPatch, use_new_descr: bool, result: str
) -> None:
    ts = Scenario()
    if use_new_descr:
        ts.set_option("use_new_descriptions_for", ["cmk_inventory"])
    ts.apply(monkeypatch)

    assert ConfigCache.service_discovery_name() == result


def test_host_ruleset_match_object_of_service(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")

    ts = Scenario()
    ts.add_host(xyz_host)
    ts.add_host(test_host, tags={TagGroupID("agent"): TagID("no-agent")})
    ts.set_autochecks(
        test_host,
        [
            AutocheckEntry(
                CheckPluginName("cpu_load"),
                None,
                {},
                {"abc": "xä"},
            )
        ],
    )
    matcher = ts.apply(monkeypatch).ruleset_matcher

    obj = matcher._service_match_object(xyz_host, "bla blä")
    assert obj == RulesetMatchObject(HostName("xyz"), "bla blä", {})

    # Funny service description because the plugin isn't loaded.
    # We could patch config.service_description, but this is easier:
    description = "Unimplemented check cpu_load"

    obj = matcher._service_match_object(test_host, description)
    service_labels = {"abc": "xä"}
    assert obj == RulesetMatchObject(HostName("test-host"), description, service_labels)


@pytest.mark.parametrize(
    "result,ruleset",
    [
        (False, None),
        (False, []),
        (False, [{"id": "01", "condition": {}, "value": None}]),
        (False, [{"id": "02", "condition": {}, "value": {}}]),
        (True, [{"id": "03", "condition": {}, "value": {"status_data_inventory": True}}]),
        (False, [{"id": "04", "condition": {}, "value": {"status_data_inventory": False}}]),
    ],
)
def test_config_cache_status_data_inventory(
    monkeypatch: MonkeyPatch, result: bool, ruleset: list[tuple] | None
) -> None:
    abc_host = HostName("abc")
    ts = Scenario()
    ts.add_host(abc_host)
    ts.set_option(
        "active_checks",
        {
            "cmk_inv": ruleset,
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.hwsw_inventory_parameters(abc_host).status_data_inventory == result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), 10),
    ],
)
def test_host_config_service_level(
    monkeypatch: MonkeyPatch, hostname: HostName, result: int | None
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "host_service_levels",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": 10,
            },
            {
                "id": "02",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": 2,
            },
        ],
    )
    config_cache = ts.apply(monkeypatch)
    assert config_cache.service_level(hostname) == result


def _rule_val(check_interval: int | None) -> dict[str, Any]:
    return {
        "check_interval": check_interval,
        "severity_unmonitored": 0,
        "severity_vanished": 0,
        "severity_new_host_label": 0,
    }


@pytest.mark.parametrize(
    "rule_entries,ignored,ping,result",
    [
        ([None], False, False, True),
        ([], False, False, False),
        ([_rule_val(None)], False, False, True),
        ([_rule_val(0)], False, False, True),
        ([_rule_val(3600)], False, False, False),
        ([_rule_val(3600)], True, False, True),
        ([_rule_val(3600)], False, True, True),
    ],
)
def test_host_config_add_discovery_check(
    monkeypatch: MonkeyPatch,
    rule_entries: Sequence[dict | None],
    ignored: bool,
    ping: bool,
    result: bool,
) -> None:
    xyz_host = HostName("xyz")
    if ping:
        tags = {
            TagGroupID("agent"): TagID("no-agent"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("piggyback"): TagID("no-piggyback"),
        }
    else:
        tags = {}

    ts = Scenario()
    ts.add_host(xyz_host, tags=tags)

    ts.set_ruleset(
        "periodic_discovery",
        [
            {
                "id": "01",
                "condition": {
                    "host_name": ["xyz"],
                },
                "value": value,
            }
            for value in rule_entries
        ],
    )
    if ignored:
        ts.set_ruleset(
            "ignored_services",
            [
                {
                    "id": "02",
                    "condition": {
                        "service_description": [{"$regex": "Check_MK inventory"}],
                        "host_name": ["xyz"],
                    },
                    "value": True,
                },
            ],
        )
    config_cache = ts.apply(monkeypatch)

    monkeypatch.setattr(config, "inventory_check_interval", 42)

    assert config_cache.discovery_check_parameters(xyz_host).commandline_only is result


def test_get_config_file_paths_with_confd(folder_path_test_config: None) -> None:
    rel_paths = [
        "%s" % p.relative_to(cmk.utils.paths.default_config_dir)
        for p in config.get_config_file_paths(with_conf_d=True)
    ]
    assert rel_paths == [
        "main.mk",
        "conf.d/wato/hosts.mk",
        "conf.d/wato/rules.mk",
        "conf.d/wato/lvl1/hosts.mk",
        "conf.d/wato/lvl1/rules.mk",
        "conf.d/wato/lvl1/lvl2/hosts.mk",
        "conf.d/wato/lvl1/lvl2/rules.mk",
        "conf.d/wato/lvl1_aaa/hosts.mk",
        "conf.d/wato/lvl1_aaa/rules.mk",
    ]


def test_load_config_folder_paths(folder_path_test_config: None) -> None:
    # reset makes our testing environment explicit and stable, but the test runs good with almost
    # any config_cache.
    config_cache = config.reset_config_cache()

    assert config_cache.host_path(HostName("main-host")) == "/"
    assert config_cache.host_path(HostName("lvl0-host")) == "/wato/"
    assert config_cache.host_path(HostName("lvl1-host")) == "/wato/lvl1/"
    assert config_cache.host_path(HostName("lvl1aaa-host")) == "/wato/lvl1_aaa/"
    assert config_cache.host_path(HostName("lvl2-host")) == "/wato/lvl1/lvl2/"

    assert config.cmc_host_rrd_config[0]["condition"]["host_folder"] == "/wato/lvl1_aaa/"
    assert config.cmc_host_rrd_config[1]["condition"]["host_folder"] == "/wato/lvl1/lvl2/"
    assert config.cmc_host_rrd_config[2]["condition"]["host_folder"] == "/wato/lvl1/"
    assert "host_folder" not in config.cmc_host_rrd_config[3]["condition"]
    assert "host_folder" not in config.cmc_host_rrd_config[4]["condition"]

    ruleset_matcher = config_cache.ruleset_matcher
    assert ruleset_matcher.get_host_values(HostName("main-host"), config.cmc_host_rrd_config) == [
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values(HostName("lvl0-host"), config.cmc_host_rrd_config) == [
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values(HostName("lvl1-host"), config.cmc_host_rrd_config) == [
        "LVL1",
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values(
        HostName("lvl1aaa-host"), config.cmc_host_rrd_config
    ) == [
        "LVL1aaa",
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values(HostName("lvl2-host"), config.cmc_host_rrd_config) == [
        "LVL2",
        "LVL1",
        "LVL0",
        "MAIN",
    ]


@pytest.fixture(name="folder_path_test_config")
def folder_path_test_config_fixture(monkeypatch: MonkeyPatch) -> Iterator[None]:
    config_dir = Path(cmk.utils.paths.check_mk_config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)

    with Path(cmk.utils.paths.main_config_file).open("w", encoding="utf-8") as f:
        f.write(
            """
all_hosts += ['%(name)s']

host_tags.update({'%(name)s': {}})

ipaddresses.update({'%(name)s': '127.0.0.1'})

host_tags.update({
    '%(name)s': {
        'piggyback': 'auto-piggyback',
        'networking': 'lan',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'snmp_ds': 'no-snmp',
        'ip-v4': 'ip-v4',
        'ip-v6': 'ip-v6',
        'site': 'unit',
        'tcp': 'tcp',
        'address_family': 'ip-v4v6',
    }
})

cmc_host_rrd_config = [
{'id':'01', 'condition': {}, 'value': 'MAIN'},
] + cmc_host_rrd_config

"""
            % {"name": "main-host"}
        )

    wato_main_folder = config_dir / "wato"
    wato_main_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_main_folder, "lvl0-host")
    _add_rule_in_folder(wato_main_folder, "LVL0")

    wato_lvl1_folder = wato_main_folder / "lvl1"
    wato_lvl1_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl1_folder, "lvl1-host")
    _add_rule_in_folder(wato_lvl1_folder, "LVL1")

    wato_lvl1a_folder = wato_main_folder / "lvl1_aaa"
    wato_lvl1a_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl1a_folder, "lvl1aaa-host")
    _add_rule_in_folder(wato_lvl1a_folder, "LVL1aaa")

    wato_lvl2_folder = wato_main_folder / "lvl1" / "lvl2"
    wato_lvl2_folder.mkdir(parents=True, exist_ok=True)
    _add_host_in_folder(wato_lvl2_folder, "lvl2-host")
    _add_rule_in_folder(wato_lvl2_folder, "LVL2")

    config.load()

    yield

    # Cleanup after the test. Would be better to use a dedicated test directory
    Path(cmk.utils.paths.main_config_file).unlink()
    (wato_main_folder / "hosts.mk").unlink()
    (wato_main_folder / "rules.mk").unlink()
    (wato_lvl1_folder / "hosts.mk").unlink()
    (wato_lvl1_folder / "rules.mk").unlink()
    (wato_lvl1a_folder / "hosts.mk").unlink()
    (wato_lvl1a_folder / "rules.mk").unlink()
    (wato_lvl2_folder / "hosts.mk").unlink()
    (wato_lvl2_folder / "rules.mk").unlink()
    (config._initialize_config())


def _add_host_in_folder(folder_path: Path, name: str) -> None:
    with (folder_path / "hosts.mk").open("w", encoding="utf-8") as f:
        f.write(
            """
all_hosts += ['%(name)s']

host_tags.update({'%(name)s': {}})

ipaddresses.update({'%(name)s': '127.0.0.1'})

host_tags.update({
    '%(name)s': {
        'piggyback': 'auto-piggyback',
        'networking': 'lan',
        'agent': 'cmk-agent',
        'criticality': 'prod',
        'snmp_ds': 'no-snmp',
        'ip-v4': 'ip-v4',
        'ip-v6': 'ip-v6',
        'site': 'unit',
        'tcp': 'tcp',
        'address_family': 'ip-v4v6',
    }
})
"""
            % {"name": name}
        )


def _add_rule_in_folder(folder_path: Path, value: str) -> None:
    with (folder_path / "rules.mk").open("w", encoding="utf-8") as f:
        if value == "LVL0":
            condition = "{}"
        else:
            condition = "{'host_folder': '/%s/' % FOLDER_PATH}"

        f.write(
            """
cmc_host_rrd_config = [
{'id': '02', 'condition': %s, 'value': '%s'},
] + cmc_host_rrd_config
"""
            % (condition, value)
        )


def _add_explicit_setting_in_folder(
    folder_path: Path, setting_name: str, values: dict[HostName, Any]
) -> None:
    folder_path.mkdir(parents=True, exist_ok=True)
    values_ = {str(k): v for k, v in values.items()}
    with (folder_path / "hosts.mk").open("w", encoding="utf-8") as f:
        f.write(
            f"""
# Explicit settings for {setting_name}
explicit_host_conf.setdefault('{setting_name}', {{}})
explicit_host_conf['{setting_name}'].update({values_})
"""
        )


def test_explicit_setting_loading() -> None:
    main_mk_file = Path(cmk.utils.paths.main_config_file)
    settings = [
        ("sub1", "parents", {HostName("hostA"): "setting1"}),
        ("sub2", "parents", {HostName("hostB"): "setting2"}),
        ("sub3", "other", {HostName("hostA"): "setting3"}),
        ("sub4", "other", {HostName("hostB"): "setting4"}),
    ]
    config_dir = Path(cmk.utils.paths.check_mk_config_dir)
    wato_main_folder = config_dir / "wato"
    try:
        main_mk_file.touch()
        for foldername, setting, values in settings:
            _add_explicit_setting_in_folder(wato_main_folder / foldername, setting, values)

        config.load()
        assert config.explicit_host_conf["parents"][HostName("hostA")] == "setting1"
        assert config.explicit_host_conf["parents"][HostName("hostB")] == "setting2"
        assert config.explicit_host_conf["other"][HostName("hostA")] == "setting3"
        assert config.explicit_host_conf["other"][HostName("hostB")] == "setting4"
    finally:
        main_mk_file.unlink()
        for foldername, _setting, _values in settings:
            shutil.rmtree(wato_main_folder / foldername, ignore_errors=True)


@pytest.fixture(name="config_path")
def fixture_config_path() -> VersionedConfigPath:
    return VersionedConfigPath(13)


def test_save_packed_config(monkeypatch: MonkeyPatch, config_path: VersionedConfigPath) -> None:
    ts = Scenario()
    ts.add_host(HostName("bla1"))
    config_cache = ts.apply(monkeypatch)
    precompiled_check_config = Path(config_path) / "precompiled_check_config.mk"

    assert not precompiled_check_config.exists()

    config.save_packed_config(config_path, config_cache)

    assert precompiled_check_config.exists()


def test_load_packed_config(config_path: VersionedConfigPath) -> None:
    config.PackedConfigStore.from_serial(config_path).write({"abc": 1})

    assert "abc" not in config.__dict__
    config.load_packed_config(config_path)
    # Mypy does not understand that we add some new member for testing
    assert config.abc == 1  # type: ignore[attr-defined]
    del config.__dict__["abc"]


class TestPackedConfigStore:
    @pytest.fixture()
    def store(self, config_path: VersionedConfigPath) -> config.PackedConfigStore:
        return config.PackedConfigStore.from_serial(config_path)

    def test_read_not_existing_file(self, store: config.PackedConfigStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.read()

    def test_write(self, store: config.PackedConfigStore, config_path: VersionedConfigPath) -> None:
        precompiled_check_config = Path(config_path) / "precompiled_check_config.mk"
        assert not precompiled_check_config.exists()

        store.write({"abc": 1})

        assert precompiled_check_config.exists()
        assert store.read() == {"abc": 1}


def test__extract_check_plugins(monkeypatch: MonkeyPatch) -> None:
    duplicate_plugin: dict[str, LegacyCheckDefinition] = {
        "duplicate_plugin": {
            "service_name": "blah",
        },
    }
    registered_plugin = CheckPluginAPI(
        name=CheckPluginName("duplicate_plugin"),
        sections=[],
        service_name="Duplicate Plugin",
        discovery_function=lambda: [],
        discovery_default_parameters=None,
        discovery_ruleset_name=None,
        discovery_ruleset_type="merged",
        check_function=lambda: [],
        cluster_check_function=None,
        check_default_parameters=None,
        check_ruleset_name=None,
        location=None,
    )

    monkeypatch.setattr(
        agent_based_register._config,
        "registered_check_plugins",
        {registered_plugin.name: registered_plugin},
    )
    monkeypatch.setattr(
        config,
        "check_info",
        duplicate_plugin,
    )
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    assert agent_based_register.is_registered_check_plugin(CheckPluginName("duplicate_plugin"))
    with pytest.raises(MKGeneralException):
        config._extract_check_plugins(validate_creation_kwargs=False)


def test__extract_agent_and_snmp_sections(monkeypatch: MonkeyPatch) -> None:
    duplicate_plugin: dict[str, dict[str, Any]] = {
        "duplicate_plugin": {},
    }
    registered_section = SNMPSectionPlugin(
        SectionName("duplicate_plugin"),
        ParsedSectionName("duplicate_plugin"),
        lambda x: None,
        lambda: (HostLabel(x, "bar") for x in ["foo"]),
        None,
        None,
        "merged",
        [],
        [],
        set(),
        None,
    )

    monkeypatch.setattr(
        agent_based_register._config,
        "registered_snmp_sections",
        {registered_section.name: registered_section},
    )
    monkeypatch.setattr(
        config,
        "check_info",
        duplicate_plugin,
    )
    monkeypatch.setattr(
        cmk.utils.debug,
        "enabled",
        lambda: True,
    )

    assert agent_based_register.is_registered_section_plugin(SectionName("duplicate_plugin"))
    config._extract_agent_and_snmp_sections()
    assert (
        agent_based_register.get_section_plugin(SectionName("duplicate_plugin"))
        == registered_section
    )
