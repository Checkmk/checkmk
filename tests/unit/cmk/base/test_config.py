#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="type-arg"


import itertools
import re
import shutil
import socket
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NoReturn

import pytest
from pytest import MonkeyPatch

import cmk.base.configlib.fetchers
import cmk.ccc.debug
import cmk.checkengine.plugin_backend as agent_based_register
import cmk.utils.paths
from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import (
    CheckPlugin,
    exists,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.base import config
from cmk.base.app import make_app
from cmk.base.config import ConfigCache, EnforcedServicesTable
from cmk.base.configlib.checkengine import CheckingConfig
from cmk.base.configlib.labels import LabelConfig
from cmk.base.configlib.loaded_config import LoadedConfigFragment
from cmk.base.configlib.servicename import (
    FinalServiceNameConfig,
    make_final_service_name_config,
    PassiveServiceNameConfig,
)
from cmk.base.default_config.base import _PeriodicDiscovery
from cmk.ccc import version as cmk_version
from cmk.ccc.config_path import VersionedConfigPath
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ccc.version import Edition
from cmk.checkengine.checkerplugin import ConfiguredService
from cmk.checkengine.discovery import (
    DiscoveryCheckParameters,
    RediscoveryParameters,
)
from cmk.checkengine.parameters import TimespecificParameters, TimespecificParameterSet
from cmk.checkengine.plugin_backend.check_plugins_legacy import convert_legacy_check_plugins
from cmk.checkengine.plugin_backend.section_plugins_legacy import convert_legacy_sections
from cmk.checkengine.plugins import (
    AutocheckEntry,
    CheckPluginName,
    InventoryPlugin,
    InventoryPluginName,
    LegacyPluginLocation,
    SectionName,
    ServiceID,
)
from cmk.checkengine.plugins import CheckPlugin as CheckPluginAPI
from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.fetchers import agent_protocol, Mode
from cmk.gui.watolib.sample_config import USE_NEW_DESCRIPTIONS_FOR_SETTING
from cmk.password_store.v1_unstable import Secret
from cmk.piggyback import backend as piggyback_backend
from cmk.server_side_calls.v1 import ActiveCheckConfig
from cmk.snmplib import SNMPBackendEnum
from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.rulesets import RuleSetName
from cmk.utils.rulesets.ruleset_matcher import BundledHostRulesetMatcher, RulesetMatcher, RuleSpec
from cmk.utils.tags import TagGroupID, TagID
from tests.testlib.unit.base_configuration_scenario import Scenario


@dataclass(frozen=True)
class _SecretsConfig:
    path: Path
    secrets: Mapping[str, Secret]


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


@pytest.mark.skip_on_code_coverage
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
def test_tcp_fetcher_config_agent_ports_matching(
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

    assert (
        cmk.base.configlib.fetchers.make_tcp_fetcher_config(
            config_cache._loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
        ).agent_port(hostname)
        == result
    )


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
    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (IPStackConfig.IPv4 in ip_lookup_config.ip_stack_config(hostname)) is result


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
    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (IPStackConfig.IPv6 in ip_lookup_config.ip_stack_config(hostname)) is result


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
    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (ip_lookup_config.ip_stack_config(hostname) is IPStackConfig.DUAL_STACK) is result


def _assert_not_called(*args: object) -> NoReturn:
    raise AssertionError(f"Unexpected call with {args}")


@pytest.mark.parametrize(
    "hostname, tags, result",
    [
        (HostName("testhost"), {TagGroupID("piggyback"): TagID("piggyback")}, True),
        (HostName("testhost"), {TagGroupID("piggyback"): TagID("no-piggyback")}, False),
    ],
)
def test_is_piggyback_host_tag_based(
    monkeypatch: MonkeyPatch, hostname: HostName, tags: dict[TagGroupID, TagID], result: bool
) -> None:
    ts = Scenario()
    ts.add_host(hostname, tags)
    assert ts.apply(monkeypatch).is_piggyback_host(hostname) == result


@pytest.mark.parametrize(
    "store_under, tags, piggyback_host_expected",
    [
        pytest.param(None, {}, False, id="no_piggyback_data"),
        pytest.param(HostAddress("testhost"), {}, True, id="data_stored_under_hostname"),
        pytest.param(HostAddress("1.2.3.4"), {}, True, id="data_stored_under_ipv4_address"),
        pytest.param(
            HostAddress("::1"),
            {TagGroupID("address_family"): TagID("ip-v6-only")},
            True,
            id="data_stored_under_ipv6_address",
        ),
    ],
)
def test_is_piggyback_host_data_based(
    monkeypatch: MonkeyPatch,
    store_under: HostAddress | None,
    tags: dict[TagGroupID, TagID],
    piggyback_host_expected: bool,
) -> None:
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(hostname, tags)
    ts.set_option("ipaddresses", {hostname: "1.2.3.4"})
    ts.set_option("ipv6addresses", {hostname: "::1"})

    if store_under is not None:
        now = time.time()
        piggyback_backend.store_piggyback_raw_data(
            source_hostname=HostName("source-host"),
            piggybacked_raw_data={store_under: (b"section data",)},
            message_timestamp=now,
            contact_timestamp=now,
            omd_root=cmk.utils.paths.omd_root,
        )

    config_cache = ts.apply(monkeypatch)

    assert config_cache.is_piggyback_host(hostname) is piggyback_host_expected


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
    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (ip_lookup_config.ip_stack_config(hostname) is IPStackConfig.NO_IP) is result


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
    ip_lookup_config = ts.apply(monkeypatch).ip_lookup_config()
    assert (ip_lookup_config.default_address_family(hostname) is socket.AF_INET6) is result


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
    assert config_cache.management_address(hostname, socket.AddressFamily.AF_INET) == result


@pytest.mark.parametrize(
    "result,attrs",
    [
        (False, {}),
        (True, {"waiting_for_discovery": True}),
        (False, {"waiting_for_discovery": False}),
    ],
)
def test_host_waiting_for_discovery(
    monkeypatch: MonkeyPatch, attrs: dict[str, str], result: bool
) -> None:
    hostname = HostName("hostname")
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_option("host_attributes", {hostname: attrs})

    config_cache = ts.apply(monkeypatch)
    assert config_cache.is_waiting_for_discovery_host(hostname) == result


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
    assert ts.apply(monkeypatch).computed_datasources(hostname).is_tcp == result


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


def test_is_not_ping_host_with_otel(monkeypatch: MonkeyPatch) -> None:
    """A host with no agent/SNMP but with OTel metrics_association is not a ping host."""
    hostname = HostName("testhost")
    ts = Scenario()
    ts.add_host(
        hostname,
        {
            TagGroupID("agent"): TagID("no-agent"),
            TagGroupID("snmp_ds"): TagID("no-snmp"),
            TagGroupID("piggyback"): TagID("no-piggyback"),
        },
    )
    ts.set_option(
        "explicit_host_conf",
        {"metrics_association": {hostname: "some_otel_config"}},
    )
    assert ts.apply(monkeypatch).is_ping_host(hostname) is False


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
    assert ts.apply(monkeypatch).computed_datasources(hostname).is_snmp is result


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
    assert ts.apply(monkeypatch).computed_datasources(hostname).is_all_agents_host is result


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
    assert ts.apply(monkeypatch).computed_datasources(hostname).is_all_special_agents_host is result


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), 5.0),
        (HostName("testhost2"), 12.0),
    ],
)
def test_make_tcp_fetcher_config_tcp_connect_timeout(
    monkeypatch: MonkeyPatch, hostname: HostName, result: float
) -> None:
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
    assert (
        cmk.base.configlib.fetchers.make_tcp_fetcher_config(
            config_cache._loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
        ).connect_timeout(hostname)
        == result
    )


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), agent_protocol.TCPEncryptionHandling.ANY_AND_PLAIN),
        (HostName("testhost2"), agent_protocol.TCPEncryptionHandling.TLS_ENCRYPTED_ONLY),
    ],
)
def test_make_tcp_fetcher_config_encryption_handling(
    monkeypatch: MonkeyPatch, hostname: HostName, result: agent_protocol.TCPEncryptionHandling
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
    assert (
        cmk.base.configlib.fetchers.make_tcp_fetcher_config(
            config_cache._loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
        ).parsed_encryption_handling(hostname)
        == result
    )


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), None),
        (HostName("testhost2"), "my-super-secret-psk"),
    ],
)
def test_make_tcp_fetcher_config_symmetric_agent_encryption(
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
    assert (
        cmk.base.configlib.fetchers.make_tcp_fetcher_config(
            config_cache._loaded_config,
            config_cache.ruleset_matcher,
            config_cache.label_manager.labels_of_host,
        ).symmetric_agent_encryption(hostname)
        == result
    )


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), []),
        (
            HostName("testhost2"),
            [
                ("abc", [{"param1": 1}]),
                ("xyz", [{"param2": 1}]),
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
        name=InventoryPluginName("lshb"),
        sections=(),
        function=lambda *args, **kw: (),
        ruleset_name=RuleSetName("if"),
        defaults={},
        location=PluginLocation("foo", "bar"),
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
                severity_changed_service_labels=0,
                severity_changed_service_params=0,
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
                severity_changed_service_labels=0,
                severity_changed_service_params=0,
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
                    "severity_changed_service_labels": 0,
                    "severity_changed_service_params": 0,
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
                    "severity_changed_service_labels": 0,
                    "severity_changed_service_params": 1,
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
                            )
                        ),
                        discovered_parameters={},
                        labels={},
                        discovered_labels={},
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
                            )
                        ),
                        discovered_parameters={},
                        labels={},
                        discovered_labels={},
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
            location=LegacyPluginLocation(""),
        )

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
    config_cache = ts.apply(monkeypatch)

    service_name_config = PassiveServiceNameConfig(
        FinalServiceNameConfig(config_cache.ruleset_matcher, "", ()), {}, {}, lambda hn: {}
    )

    assert (
        EnforcedServicesTable(
            BundledHostRulesetMatcher(
                config_cache._loaded_config.static_checks,
                config_cache.ruleset_matcher,
                config_cache.label_manager.labels_of_host,
            ),
            service_name_config,
            {
                pn: make_plugin(pn)
                for pn in (CheckPluginName("checktype1"), CheckPluginName("checktype2"))
            },
        )(hostname)
        == result
    )


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


@pytest.mark.parametrize(
    "hostname, result",
    [
        (HostName("testhost1"), {}),
        (HostName("testhost2"), {SectionName("snmp_uptime"): 240}),
    ],
)
def test_snmp_check_interval(
    monkeypatch: MonkeyPatch, hostname: HostName, result: Mapping[SectionName, int | None]
) -> None:
    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset(
        "snmp_check_interval",
        [
            {
                "id": "01",
                "condition": {"host_name": [HostName("testhost2")]},
                "value": (["snmp_uptime"], ("cached", 240)),
            },
        ],
    )
    assert ts.apply(monkeypatch).snmp_fetch_intervals(hostname) == result


@pytest.fixture(name="service_list")
def _service_list() -> list[ConfiguredService]:
    return [
        ConfiguredService(
            check_plugin_name=CheckPluginName("plugin_%s" % d),
            item="item",
            description="description %s" % d,
            parameters=TimespecificParameters(),
            discovered_parameters={},
            labels={},
            discovered_labels={},
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

    monkeypatch.setattr(config_cache, "_sorted_services", lambda *args: service_list)
    services = config_cache.configured_services(
        host_name,
        {},
        config_cache.make_service_configurer({}, lambda *a: ""),
        lambda *a: "",
        enforced_services_table=lambda hn: {},
        service_depends_on=lambda hn, descr: {
            "description A": ["description C"],
            "description B": ["description D"],
            "description D": ["description A", "description F"],
        }.get(descr, []),
    )
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

    monkeypatch.setattr(config_cache, "_sorted_services", lambda *args: service_list)

    with pytest.raises(
        MKGeneralException,
        match=re.escape(
            "Cyclic service dependency of host MyHost:"
            " 'description D' (plugin_D / item),"
            " 'description A' (plugin_A / item),"
            " 'description B' (plugin_B / item)"
        ),
    ):
        config_cache.configured_services(
            HostName("MyHost"),
            {},
            config_cache.make_service_configurer({}, lambda *a: ""),
            lambda *a: "",
            enforced_services_table=lambda hn: {},
            service_depends_on=lambda _hn, descr: {
                "description A": ["description B"],
                "description B": ["description D"],
                "description D": ["description A"],
            }.get(descr, []),
        )


def test_service_depends_on_unknown_host(monkeypatch: MonkeyPatch) -> None:
    config_cache = Scenario().apply(monkeypatch)
    service_depends_on = config.ServiceDependsOn(
        tag_list=config_cache.host_tags.tag_list, service_dependencies=()
    )
    assert not service_depends_on(HostName("test-host"), "svc")


def test_service_depends_on(monkeypatch: MonkeyPatch) -> None:
    test_host = HostName("test-host")
    ts = Scenario()
    ts.add_host(test_host)
    config_cache = ts.apply(monkeypatch)

    service_depends_on = config.ServiceDependsOn(
        tag_list=config_cache.host_tags.tag_list,
        service_dependencies=[
            ("dep1", [], config.ALL_HOSTS, ["svc1"], {}),
            ("dep2-%s", [], config.ALL_HOSTS, ["svc1-(.*)"], {}),
            ("dep-disabled", [], config.ALL_HOSTS, ["svc1"], {"disabled": True}),
        ],
    )

    assert not service_depends_on(test_host, "svc2")
    assert service_depends_on(test_host, "svc1") == ["dep1"]
    assert service_depends_on(test_host, "svc1-abc") == ["dep1", "dep2-abc"]


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
    assert list(cluster_config.clusters_of(HostName("node1"))) == ["cluster1"]
    assert not list(cluster_config.clusters_of(HostName("host1")))
    assert not list(cluster_config.clusters_of(HostName("cluster1")))


def test_config_cache_nodes(cluster_config: ConfigCache) -> None:
    assert not list(cluster_config.nodes(HostName("node1")))
    assert not list(cluster_config.nodes(HostName("host1")))
    assert list(cluster_config.nodes(HostName("cluster1"))) == ["node1"]


def test_host_config_parents(cluster_config: ConfigCache) -> None:
    assert not list(cluster_config.parents(HostName("node1")))
    assert not list(cluster_config.parents(HostName("host1")))
    # TODO: Move cluster/node parent handling to HostConfig
    # assert cluster_config.make_cee_host_config("cluster1").parents == ["node1"]
    assert not list(cluster_config.parents(HostName("cluster1")))


def test_config_cache_tag_list_of_host(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    test_host = HostName("test-host")
    xyz_host = HostName("xyz")
    ts.add_host(test_host, tags={TagGroupID("agent"): TagID("no-agent")})
    ts.add_host(xyz_host)

    config_cache = ts.apply(monkeypatch)
    assert set(config_cache.host_tags.tag_list(xyz_host)) == {
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
    assert set(config_cache.host_tags.tag_list(HostName("not-existing"))) == {
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
    assert config_cache.host_tags.tags(xyz_host) == {
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
    assert config_cache.host_tags.tags(test_host) == {
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

    assert config_cache.host_tags.tags(xyz_host) == {
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
    assert config_cache.tags_of_service(xyz_host, "CPU load", {}) == {}

    assert config_cache.host_tags.tags(test_host) == {
        "address_family": "ip-v4-only",
        "agent": "no-agent",
        "criticality": "prod",
        "ip-v4": "ip-v4",
        "networking": "lan",
        "piggyback": "auto-piggyback",
        "site": "unit",
        "snmp_ds": "no-snmp",
    }
    assert config_cache.tags_of_service(test_host, "CPU load", {}) == {"criticality": "prod"}


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
    assert config_cache.label_manager.labels_of_host(xyz_host) == {"cmk/site": "unit"}
    assert config_cache.label_manager.labels_of_host(test_host) == {
        "cmk/site": "unit",
        "explicit": "ding",
        "from-rule": "rule1",
        "from-rule2": "rule2",
    }
    assert config_cache.label_manager.label_sources_of_host(test_host) == {
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
    assert config_cache.label_manager.labels_of_host(test_host) == {
        "cmk/site": "unit",
        "äzzzz": "eeeeez",
    }
    assert config_cache.label_manager.label_sources_of_host(test_host) == {
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
    assert config_cache.extra_attributes_of_service(hostname, "CPU load", {}) == result


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
    assert config_cache.servicegroups_of_service(hostname, "CPU load", {}) == result


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
    assert sorted(config_cache.contactgroups_of_service(hostname, "CPU load", {})) == sorted(result)


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
    assert config_cache.check_period_of_passive_service(hostname, "CPU load", {}) == result


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
    assert config_cache.custom_attributes_of_service(hostname, "CPU load", {}) == result


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
    ts.add_to_ruleset_bundle(
        "extra_service_conf",
        "_ec_sl",
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
    assert config_cache.service_level_of_service(hostname, "CPU load", {}) == result


@pytest.mark.parametrize(
    "hostname,result",
    [
        (HostName("testhost1"), "24X7"),
        (HostName("testhost2"), "24X7"),
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
    assert config_cache.check_period_of_passive_service(hostname, "CPU load", {}) == result


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
    config_cache = ts.apply(monkeypatch)

    assert clu in config_cache.hosts_config.clusters
    assert config_cache.max_cachefile_age(clu).get(Mode.CHECKING) != config.check_max_cachefile_age
    assert (
        config_cache.max_cachefile_age(clu).get(Mode.CHECKING) == config.cluster_max_cachefile_age
    )


@pytest.mark.parametrize(
    "use_new_descr,result",
    [
        pytest.param({"cmk_inventory": True}, "Check_MK Discovery", id="new description"),
        pytest.param({"cmk_inventory": False}, "Check_MK inventory", id="old description"),
        pytest.param(
            USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"],
            "Check_MK Discovery",
            id="from sample config",
        ),
        pytest.param({}, "Check_MK inventory", id="default config"),
    ],
)
def test_config_cache_service_discovery_name(
    monkeypatch: MonkeyPatch, use_new_descr: dict[str, bool], result: str
) -> None:
    ts = Scenario()
    ts.set_option("use_new_descriptions_for", use_new_descr)

    ts.apply(monkeypatch)

    assert ConfigCache.service_discovery_name() == result


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
    ts.add_to_ruleset_bundle(
        "extra_host_conf",
        "_ec_sl",
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


def _rule_val(check_interval: int) -> _PeriodicDiscovery:
    return _PeriodicDiscovery(
        severity_unmonitored=0,
        severity_vanished=0,
        severity_changed_service_labels=0,
        severity_changed_service_params=0,
        severity_new_host_label=0,
        check_interval=check_interval,
        inventory_rediscovery=RediscoveryParameters(),
    )


@pytest.mark.parametrize(
    "rule_entries,ignored,ping,result",
    [
        ([None], False, False, True),
        ([], False, False, False),
        ([_rule_val(0)], False, False, True),
        ([_rule_val(3600)], False, False, False),
        ([_rule_val(3600)], True, False, True),
        ([_rule_val(3600)], False, True, True),
    ],
)
def test_host_config_add_discovery_check(
    monkeypatch: MonkeyPatch,
    rule_entries: Sequence[_PeriodicDiscovery | None],
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
    ts.set_option("inventory_check_interval", 42)
    config_cache = ts.apply(monkeypatch)

    assert config_cache.discovery_check_parameters(xyz_host).commandline_only is result


def test_get_config_file_paths_with_confd(
    folder_path_test_config: LoadedConfigFragment,
) -> None:
    # NOTE: there are still some globals at play here, otherwise we would have to use
    # the folder_path_test_config somewhere.
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


def test_load_config_folder_paths(folder_path_test_config: LoadedConfigFragment) -> None:
    config_cache = config.ConfigCache(
        folder_path_test_config,
        make_app(Edition.COMMUNITY).get_builtin_host_labels,
        Edition.COMMUNITY,
    )

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
    assert ruleset_matcher.get_host_values_all(
        HostName("main-host"), config.cmc_host_rrd_config, lambda hn: {}
    ) == [
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values_all(
        HostName("lvl0-host"), config.cmc_host_rrd_config, lambda hn: {}
    ) == [
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values_all(
        HostName("lvl1-host"), config.cmc_host_rrd_config, lambda hn: {}
    ) == [
        "LVL1",
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values_all(
        HostName("lvl1aaa-host"), config.cmc_host_rrd_config, lambda hn: {}
    ) == [
        "LVL1aaa",
        "LVL0",
        "MAIN",
    ]
    assert ruleset_matcher.get_host_values_all(
        HostName("lvl2-host"), config.cmc_host_rrd_config, lambda hn: {}
    ) == [
        "LVL2",
        "LVL1",
        "LVL0",
        "MAIN",
    ]


@pytest.fixture(name="folder_path_test_config")
def folder_path_test_config_fixture(
    monkeypatch: MonkeyPatch,
) -> Iterator[LoadedConfigFragment]:
    config_dir = cmk.utils.paths.check_mk_config_dir
    config_dir.mkdir(parents=True, exist_ok=True)

    with cmk.utils.paths.main_config_file.open("w", encoding="utf-8") as f:
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

    _edition = Edition.COMMUNITY
    yield config.load(
        discovery_rulesets=(),
        get_builtin_host_labels=make_app(_edition).get_builtin_host_labels,
        edition=_edition,
    ).loaded_config

    # Cleanup after the test. Would be better to use a dedicated test directory
    cmk.utils.paths.main_config_file.unlink()
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


def test_explicit_setting_loading(patch_omd_site: None) -> None:
    main_mk_file = cmk.utils.paths.main_config_file
    settings = [
        ("sub1", "parents", {HostName("hostA"): "setting1"}),
        ("sub2", "parents", {HostName("hostB"): "setting2"}),
        ("sub3", "other", {HostName("hostA"): "setting3"}),
        ("sub4", "other", {HostName("hostB"): "setting4"}),
    ]
    config_dir = cmk.utils.paths.check_mk_config_dir
    wato_main_folder = config_dir / "wato"
    try:
        main_mk_file.touch()
        for foldername, setting, values in settings:
            _add_explicit_setting_in_folder(wato_main_folder / foldername, setting, values)

        _edition = Edition.COMMUNITY
        config.load(
            discovery_rulesets=(),
            get_builtin_host_labels=make_app(_edition).get_builtin_host_labels,
            edition=_edition,
        )
        assert config.explicit_host_conf["parents"][HostName("hostA")] == "setting1"
        assert config.explicit_host_conf["parents"][HostName("hostB")] == "setting2"
        assert config.explicit_host_conf["other"][HostName("hostA")] == "setting3"
        assert config.explicit_host_conf["other"][HostName("hostB")] == "setting4"
    finally:
        main_mk_file.unlink()
        for foldername, _setting, _values in settings:
            shutil.rmtree(wato_main_folder / foldername, ignore_errors=True)


@pytest.fixture(name="config_path")
def fixture_config_path() -> Path:
    return Path(VersionedConfigPath(cmk.utils.paths.omd_root, 13))


def test_save_packed_config(monkeypatch: MonkeyPatch, config_path: Path) -> None:
    ts = Scenario()
    ts.add_host(HostName("bla1"))
    config_cache = ts.apply(monkeypatch)
    precompiled_check_config = config_path / "precompiled_check_config.mk"

    assert not precompiled_check_config.exists()

    config.save_packed_config(config_path, config_cache, {})

    assert precompiled_check_config.exists()


def test_load_packed_config(config_path: Path) -> None:
    config.PackedConfigStore.from_serial(config_path).write({"abcd": 1})

    assert "abcd" not in config.__dict__
    _edition = Edition.COMMUNITY
    config.load_packed_config(
        config_path,
        discovery_rulesets=(),
        get_builtin_host_labels=make_app(_edition).get_builtin_host_labels,
        edition=_edition,
    )
    # Mypy does not understand that we add some new member for testing
    assert config.abcd == 1  # type: ignore[attr-defined]
    del config.__dict__["abcd"]


class TestPackedConfigStore:
    @pytest.fixture()
    def store(self, config_path: Path) -> config.PackedConfigStore:
        return config.PackedConfigStore.from_serial(config_path)

    def test_read_not_existing_file(self, store: config.PackedConfigStore) -> None:
        with pytest.raises(FileNotFoundError):
            store.read()

    def test_write(self, store: config.PackedConfigStore, config_path: Path) -> None:
        precompiled_check_config = config_path / "precompiled_check_config.mk"
        assert not precompiled_check_config.exists()

        store.write({"abc": 1})

        assert precompiled_check_config.exists()
        assert store.read() == {"abc": 1}


def test__extract_check_plugins(monkeypatch: MonkeyPatch) -> None:
    duplicate_legacy_plugin = LegacyCheckDefinition(
        name="duplicate_plugin",
        service_name="blah",
        check_function=lambda: [],
    )

    def _noop_disco(section: None) -> Iterable[Service]:
        yield from ()

    def _noop_check(section: None) -> Iterable[Result]:
        yield from ()

    new_style_plugin = CheckPlugin(
        name="duplicate_plugin",
        service_name="Duplicate Plug-in new style",
        discovery_function=_noop_disco,
        check_function=_noop_check,
    )

    monkeypatch.setattr(
        agent_based_register._discover,
        "discover_all_plugins",
        lambda *a, **kw: DiscoveredPlugins(
            errors=(), plugins={PluginLocation(module="module", name="name"): new_style_plugin}
        ),
    )
    converted_legacy_checks = convert_legacy_check_plugins(
        (duplicate_legacy_plugin,),
        {duplicate_legacy_plugin.name: "/path/to/duplicate_legacy_plugin.py"},
        validate_creation_kwargs=False,
        raise_errors=True,
    )[1]
    assert converted_legacy_checks
    # new check plugins should win silently:
    plugins = agent_based_register.load_all_plugins(
        sections=(),
        checks=converted_legacy_checks,
        legacy_errors=(),
        raise_errors=True,
    )
    # It's a new style plugin:
    assert (
        plugins.check_plugins[CheckPluginName("duplicate_plugin")].service_name
        == "Duplicate Plug-in new style"
    )


def test__extract_agent_and_snmp_sections(monkeypatch: MonkeyPatch) -> None:
    duplicate_plugin = (LegacyCheckDefinition(name="duplicate_plugin"),)

    def dummy_parse_function(string_table: StringTable) -> int:
        return 42

    new_style_section = SimpleSNMPSection(
        name="duplicate_plugin",
        detect=exists(".1.2.3"),
        fetch=SNMPTree(base=".1.2.3", oids=[]),
        parse_function=dummy_parse_function,
    )

    monkeypatch.setattr(
        agent_based_register._discover,
        "discover_all_plugins",
        lambda *a, **kw: DiscoveredPlugins(
            errors=(), plugins={PluginLocation(module="module", name="name"): new_style_section}
        ),
    )

    plugins = agent_based_register.load_all_plugins(
        sections=convert_legacy_sections(duplicate_plugin, {}, raise_errors=True)[1],
        checks=(),
        legacy_errors=(),
        raise_errors=True,  # we don't expect any errors
    )
    assert plugins.snmp_sections[SectionName("duplicate_plugin")].detect_spec


@pytest.mark.parametrize(
    ["nodes", "expected"],
    [
        pytest.param(
            [HostName("node1"), HostName("node2")],
            config.HostCheckTable(
                services=[
                    ConfiguredService(
                        check_plugin_name=CheckPluginName("check1"),
                        item="item",
                        description="Unimplemented check check1 / item",
                        parameters=TimespecificParameters(
                            (
                                TimespecificParameterSet({"origin": "enforced1"}, ()),
                                TimespecificParameterSet({}, ()),
                            )
                        ),
                        discovered_parameters={},
                        labels={},
                        discovered_labels={},
                        is_enforced=True,
                    )
                ]
            ),
            id="discovered_last",
        ),
        pytest.param(
            [HostName("node2"), HostName("node1")],
            config.HostCheckTable(
                services=[
                    ConfiguredService(
                        check_plugin_name=CheckPluginName("check1"),
                        item="item",
                        description="Unimplemented check check1 / item",
                        parameters=TimespecificParameters(
                            (
                                TimespecificParameterSet({"origin": "enforced1"}, ()),
                                TimespecificParameterSet({}, ()),
                            )
                        ),
                        discovered_parameters={},
                        labels={},
                        discovered_labels={},
                        is_enforced=True,
                    )
                ]
            ),
            id="enforced last",
        ),
    ],
)
def test_check_table_cluster_merging_enforced_and_discovered(
    monkeypatch: MonkeyPatch, nodes: Sequence[HostName], expected: config.HostCheckTable
) -> None:
    ts = Scenario()
    ts.add_host(N1 := HostName("node1"))
    ts.add_host(N2 := HostName("node2"))
    ts.add_cluster(CN := HostName("cluster"), nodes=nodes)
    ts.set_ruleset(
        "clustered_services", [{"id": "01", "condition": {}, "value": True}]
    )  # cluster everything everywhere
    ts.set_ruleset_bundle(
        "static_checks",
        {
            "rule_name": [
                {
                    "id": "01",
                    "condition": {"host_name": [str(N1)]},
                    "value": ("check1", "item", {"origin": "enforced1"}),
                },
            ]
        },
    )
    ts.set_autochecks(
        N2,
        [AutocheckEntry(CheckPluginName("check1"), "item", {}, {})],
    )
    config_cache = ts.apply(monkeypatch)
    service_name_config = config_cache.make_passive_service_name_config(
        make_final_service_name_config(config_cache._loaded_config, config_cache.ruleset_matcher)
    )

    assert (
        config_cache.check_table(
            CN,
            {},
            config_cache.make_service_configurer({}, service_name_config),
            service_name_config,
            EnforcedServicesTable(
                BundledHostRulesetMatcher(
                    config_cache._loaded_config.static_checks,
                    config_cache.ruleset_matcher,
                    config_cache.label_manager.labels_of_host,
                ),
                service_name_config,
                {},
            ),
        )
        == expected
    )


def test_collect_passwords_includes_non_matching_rulesets(monkeypatch: MonkeyPatch) -> None:
    ts = Scenario()
    ts.set_ruleset_bundle(
        "active_checks",
        {
            "some_active_check": [
                {
                    "id": "01",
                    "condition": {"host_name": ["no-such-host"]},
                    "value": {
                        "secret": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("uuid1234", "p4ssw0rd!"),
                        )
                    },
                }
            ],
        },
    )
    config_cache = ts.apply(monkeypatch)

    assert config_cache.collect_passwords() == {"uuid1234": Secret("p4ssw0rd!")}


def test_get_active_service_data_crash(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cmk.ccc.debug, cmk.ccc.debug.enabled.__name__, lambda: False)
    monkeypatch.setattr(
        config,
        "load_active_checks",
        lambda **kw: {
            PluginLocation(
                "cmk.plugins.my_stuff.server_side_calls", "active_check_my_active_check"
            ): ActiveCheckConfig(
                name="my_active_check",
                parameter_parser=lambda p: p,
                commands_function=lambda *a, **kw: 1 / 0,  # type: ignore[arg-type]
            )
        },
    )
    host_name = HostName("test_host")
    ts = Scenario()
    ts.add_host(host_name)
    ts.set_ruleset_bundle(
        "active_checks",
        {
            "my_active_check": [
                {
                    "condition": {},
                    "id": "2",
                    "value": {"description": "My active check", "param1": "param1"},
                }
            ]
        },
    )
    config_cache = ts.apply(monkeypatch)

    list(
        config_cache.active_check_services(
            host_name,
            IPStackConfig.IPv4,
            socket.AddressFamily.AF_INET,
            config_cache.get_host_attributes(
                host_name, socket.AddressFamily.AF_INET, lambda *a, **kw: HostAddress("")
            ),
            FinalServiceNameConfig(config_cache.ruleset_matcher, "", ()),
            lambda *a, **kw: HostAddress(""),
            _SecretsConfig(path=Path(), secrets={}),
            for_relay=False,
        )
    )

    captured = capsys.readouterr()
    assert (
        captured.err
        == "\nWARNING: Config creation for active check my_active_check failed on test_host: division by zero\n"
    )


class TestLabelsConfig:
    def test_host_labels(self) -> None:
        test_host = HostName("test-host")
        xyz_host = HostName("xyz")
        ruleset_matcher = RulesetMatcher(
            host_tags={test_host: {TagGroupID("agent"): TagID("no-agent")}, xyz_host: {}},
            host_paths={},
            all_configured_hosts=frozenset([test_host, xyz_host]),
            clusters_of={},
            nodes_of={},
        )

        config = LabelConfig(
            ruleset_matcher,
            host_label_rules=(
                {
                    "condition": {
                        "host_name": [str(xyz_host)],
                    },
                    "id": "01",
                    "value": {"label": "val1"},
                },
                {
                    "condition": {
                        "host_tags": {TagGroupID("agent"): TagID("no-agent")},
                    },
                    "id": "02",
                    "value": {"label": "val2"},
                },
            ),
            service_label_rules=(),
        )

        assert config.host_labels(xyz_host) == {"label": "val1"}
        assert config.host_labels(test_host) == {"label": "val2"}

    def test_service_labels(self) -> None:
        test_host = HostName("test-host")
        xyz_host = HostName("xyz")
        ruleset_matcher = RulesetMatcher(
            host_tags={test_host: {TagGroupID("agent"): TagID("no-agent")}, xyz_host: {}},
            host_paths={},
            all_configured_hosts=frozenset([test_host, xyz_host]),
            clusters_of={},
            nodes_of={},
        )

        config = LabelConfig(
            ruleset_matcher,
            host_label_rules=(),
            service_label_rules=(
                {
                    "condition": {
                        "host_name": [str(xyz_host)],
                    },
                    "id": "01",
                    "value": {"label": "val1"},
                },
                {
                    "condition": {
                        "host_tags": {TagGroupID("agent"): TagID("no-agent")},
                    },
                    "id": "02",
                    "value": {"label": "val2"},
                },
            ),
        )
        assert config.service_labels(xyz_host, "CPU load", lambda h: {}) == {"label": "val1"}
        assert config.service_labels(test_host, "CPU load", lambda h: {}) == {
            "label": "val2",
        }


@pytest.mark.parametrize(
    "check_group_parameters",
    [
        {},
        {
            "levels": (4, 5, 6, 7),
        },
    ],
)
def test_checking_config(
    monkeypatch: MonkeyPatch, check_group_parameters: Mapping[str, object]
) -> None:
    hostname = HostName("hostname")

    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)

    config_getter = CheckingConfig(
        config_cache.ruleset_matcher,
        lambda hn: {},
        {
            "ps": [
                {
                    "id": "02",
                    "condition": {"service_description": [], "host_name": [hostname]},
                    "options": {},
                    "value": check_group_parameters,
                }
            ],
        },
        ("ps",),
    )

    entries = config_getter(hostname, "item", {}, "ps")

    assert len(entries) == 1
    assert entries[0] == check_group_parameters


_KNOWN_EXCEPTIONS = frozenset(
    [  # handled in ConfigCache.service_discovery_name()
        "cmk_inventory",
        # handled in cmk.update_config.plugins.actions.rulesets._force_old_http_service_description
        "http",
        # TODO investigate if bug, cmk.base.config._old_service_descriptions uses key "hyperv_vm",
        #  but cmk.gui.watolib.sample_config.USE_NEW_DESCRIPTIONS_FOR_SETTING uses "hyperv_vms"
        "hyperv_vms",
        # TODO investigate if bug, missing in cmk.base.config._old_service_descriptions
        "megaraid_vdisks",
    ]
)


@dataclass(frozen=True)
class TestServiceDescription:
    item: str
    service_description: str


_EXPECTED_OLD_DESCRIPTIONS = {
    "aix_memory": TestServiceDescription("test_item", "Memory used test_item"),
    "barracuda_mailqueues": TestServiceDescription("test_item", "Mail Queue"),
    "brocade_sys_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "casa_cpu_temp": TestServiceDescription("test_item", "Temperature test_item"),
    "cisco_mem": TestServiceDescription("test_item", "Mem used test_item"),
    "cisco_mem_asa": TestServiceDescription("test_item", "Mem used test_item"),
    "cisco_mem_asa64": TestServiceDescription("test_item", "Mem used test_item"),
    "cmciii_psm_current": TestServiceDescription("test_item", "test_item"),
    "cmciii_temp": TestServiceDescription("Ambient Foo", "Foo Temperature"),
    "cmciii_lcp_airin": TestServiceDescription("test_item", "LCP Fanunit Air IN test_item"),
    "cmciii_lcp_airout": TestServiceDescription("test_item", "LCP Fanunit Air OUT test_item"),
    "cmciii_lcp_water": TestServiceDescription("test_item", "LCP Fanunit Water test_item"),
    "db2_mem": TestServiceDescription("test_item", "Mem of test_item"),
    "df": TestServiceDescription("test_item", "fs_test_item"),
    "df_netapp": TestServiceDescription("test_item", "fs_test_item"),
    "df_netapp32": TestServiceDescription("test_item", "fs_test_item"),
    "docker_container_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "enterasys_temp": TestServiceDescription("test_item", "Temperature"),
    "esx_vsphere_datastores": TestServiceDescription("test_item", "fs_test_item"),
    "esx_vsphere_hostsystem_mem_usage": TestServiceDescription(
        "test_item", "Memory used test_item"
    ),
    "esx_vsphere_hostsystem_mem_usage_cluster": TestServiceDescription(
        "test_item", "Memory usage test_item"
    ),
    "etherbox_temp": TestServiceDescription("test_item", "Sensor test_item"),
    "fortigate_memory": TestServiceDescription("test_item", "Memory usage test_item"),
    "fortigate_memory_base": TestServiceDescription("test_item", "Memory usage test_item"),
    "fortigate_node_memory": TestServiceDescription("test_item", "Memory usage test_item"),
    "hr_fs": TestServiceDescription("test_item", "fs_test_item"),
    "hr_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "huawei_switch_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "ibm_svc_mdiskgrp": TestServiceDescription("test_item", "MDiskGrp test_item"),
    "ibm_svc_system": TestServiceDescription("test_item", "IBM SVC Info test_item"),
    "ibm_svc_systemstats_cache": TestServiceDescription(
        "test_item", "IBM SVC Cache Total test_item"
    ),
    "ibm_svc_systemstats_disk_latency": TestServiceDescription(
        "test_item", "IBM SVC Latency test_item Total"
    ),
    "ibm_svc_systemstats_diskio": TestServiceDescription(
        "test_item", "IBM SVC Throughput test_item Total"
    ),
    "ibm_svc_systemstats_iops": TestServiceDescription("test_item", "IBM SVC IOPS test_item Total"),
    "innovaphone_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "innovaphone_temp": TestServiceDescription("test_item", "Temperature"),
    "juniper_mem": TestServiceDescription("test_item", "Memory Utilization test_item"),
    "juniper_screenos_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "juniper_trpz_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "liebert_bat_temp": TestServiceDescription("test_item", "Battery Temp"),
    "logwatch": TestServiceDescription("test_item", "LOG test_item"),
    "logwatch_groups": TestServiceDescription("test_item", "LOG test_item"),
    "mem_used": TestServiceDescription("test_item", "Memory used test_item"),
    "mem_win": TestServiceDescription("test_item", "Memory and pagefile test_item"),
    "megaraid_bbu": TestServiceDescription("test_item", "RAID Adapter/BBU test_item"),
    "megaraid_pdisks": TestServiceDescription("test_item", "RAID PDisk Adapt/Enc/Sl test_item"),
    "megaraid_ldisks": TestServiceDescription("test_item", "RAID Adapter/LDisk test_item"),
    "mknotifyd": TestServiceDescription("test_item", "Notification Spooler test_item"),
    "mknotifyd_connection": TestServiceDescription(
        "test_item", "Notification Connection test_item"
    ),
    "mssql_backup": TestServiceDescription("test_item", "test_item Backup"),
    "mssql_blocked_sessions": TestServiceDescription("test_item", "MSSQL Blocked Sessions"),
    "mssql_counters_cache_hits": TestServiceDescription("test_item", "test_item"),
    "mssql_counters_file_sizes": TestServiceDescription("test_item", "test_item File Sizes"),
    "mssql_counters_locks": TestServiceDescription("test_item", "test_item Locks"),
    "mssql_counters_locks_per_batch": TestServiceDescription(
        "test_item", "test_item Locks per Batch"
    ),
    "mssql_counters_pageactivity": TestServiceDescription("test_item", "test_item Page Activity"),
    "mssql_counters_sqlstats": TestServiceDescription("test_item", "test_item"),
    "mssql_counters_transactions": TestServiceDescription("test_item", "test_item Transactions"),
    "mssql_databases": TestServiceDescription("test_item", "test_item Database"),
    "mssql_datafiles": TestServiceDescription("test_item", "Datafile test_item"),
    "mssql_tablespaces": TestServiceDescription("test_item", "test_item Sizes"),
    "mssql_transactionlogs": TestServiceDescription("test_item", "Transactionlog test_item"),
    "mssql_versions": TestServiceDescription("test_item", "test_item Version"),
    "netapp_ontap_volumes": TestServiceDescription("svm:vol", "Volume svm.vol"),
    "netapp_ontap_snapshots": TestServiceDescription("svm:vol", "Snapshots Volume svm.vol"),
    "netscaler_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "nullmailer_mailq": TestServiceDescription("test_item", "Nullmailer Queue"),
    "nvidia_temp": TestServiceDescription("test_item", "Temperature NVIDIA test_item"),
    "postfix_mailq": TestServiceDescription("test_item", "Postfix Queue test_item"),
    "ps": TestServiceDescription("test_item", "proc_test_item"),
    "qmail_stats": TestServiceDescription("test_item", "Qmail Queue"),
    "raritan_emx": TestServiceDescription("test_item", "Rack test_item"),
    "raritan_pdu_inlet": TestServiceDescription("test_item", "Input Phase test_item"),
    "services": TestServiceDescription("test_item", "service_test_item"),
    "solaris_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "sophos_memory": TestServiceDescription("test_item", "Memory usage test_item"),
    "statgrab_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "tplink_mem": TestServiceDescription("test_item", "Memory used test_item"),
    "ups_bat_temp": TestServiceDescription("test_item", "Temperature Battery test_item"),
    "vms_diskstat_df": TestServiceDescription("test_item", "fs_test_item"),
    "wmic_process": TestServiceDescription("test_item", "proc_test_item"),
    "zfsget": TestServiceDescription("test_item", "fs_test_item"),
    "prism_alerts": TestServiceDescription("test_item", "Prism Alerts"),
    "prism_containers": TestServiceDescription("test_item", "Containers test_item"),
    "prism_info": TestServiceDescription("test_item", "Prism Cluster"),
    "prism_storage_pools": TestServiceDescription("test_item", "Storage Pool test_item"),
}


def test_new_description_used_for_plugins_configured_via_use__new_descriptions_for(
    monkeypatch: MonkeyPatch,
) -> None:
    test_host = HostAddress("test_host")

    ts = Scenario()
    ts.add_host(test_host)
    config_cache = ts.apply(monkeypatch)

    adapted_sample_config = {
        k: True
        for k in USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
        if k not in _KNOWN_EXCEPTIONS
    }
    test_item = "test_item"
    for plugin_name in adapted_sample_config:
        service_name_config = PassiveServiceNameConfig(
            FinalServiceNameConfig(config_cache.ruleset_matcher, "", ()),
            {},
            adapted_sample_config,
            lambda hn: {},
        )

        actual_descr = service_name_config(
            test_host, ServiceID(CheckPluginName(plugin_name), test_item), "Service %s"
        )
        assert actual_descr == f"Service {test_item}"


@pytest.mark.parametrize(
    ["plugin_name", "service_name_template", "expected_descr"],
    [
        pytest.param(
            "test_plugin_never_seen_before",
            "New service description %s",
            "New service description test_item",
            id="not configured",
        ),
        pytest.param(
            "cisco_mem_asa64", "Mem used %s", "Mem used test_item", id="previously configured"
        ),
    ],
)
def test_correct_description_used_for_plugins_not_configured_via__use_new_descriptions_for(
    monkeypatch: MonkeyPatch, plugin_name: str, service_name_template: str, expected_descr: str
) -> None:
    test_host = HostAddress("test_host")

    ts = Scenario()
    ts.add_host(test_host)
    config_cache = ts.apply(monkeypatch)

    service_name_config = PassiveServiceNameConfig(
        FinalServiceNameConfig(config_cache.ruleset_matcher, "", ()),
        {},
        {},
        lambda hn: {},
    )

    actual_descr = service_name_config(
        test_host, ServiceID(CheckPluginName(plugin_name), "test_item"), service_name_template
    )
    assert actual_descr == expected_descr


def test_old_description_used(monkeypatch: MonkeyPatch) -> None:
    test_host = HostAddress("test_host")

    adapted_sample_config = {
        k: False
        for k in USE_NEW_DESCRIPTIONS_FOR_SETTING["use_new_descriptions_for"]
        if k not in _KNOWN_EXCEPTIONS
    }

    ts = Scenario()
    ts.add_host(test_host)
    config_cache = ts.apply(monkeypatch)

    for plugin_name in adapted_sample_config:
        expected = _EXPECTED_OLD_DESCRIPTIONS[plugin_name]

        service_name_config = PassiveServiceNameConfig(
            FinalServiceNameConfig(config_cache.ruleset_matcher, "", ()),
            {},
            adapted_sample_config,
            lambda hn: {},
        )

        actual_descr = service_name_config(
            test_host,
            ServiceID(CheckPluginName(plugin_name), expected.item),
            "Service %s",
        )
        assert actual_descr == expected.service_description


def test_notification_spooling_community_default_is_off(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(config, "notification_spool_to", None)
    monkeypatch.setattr(config, "notification_spooling", None)
    monkeypatch.setattr(cmk_version, "edition", lambda _omd_root: Edition.COMMUNITY)
    assert ConfigCache.notification_spooling() == "off"


@pytest.mark.parametrize(
    "edition",
    [Edition.PRO, Edition.CLOUD, Edition.ULTIMATE, Edition.ULTIMATEMT],
)
def test_notification_spooling_non_community_default_is_local(
    monkeypatch: MonkeyPatch, edition: Edition
) -> None:
    monkeypatch.setattr(config, "notification_spool_to", None)
    monkeypatch.setattr(config, "notification_spooling", None)
    monkeypatch.setattr(cmk_version, "edition", lambda _omd_root: edition)
    assert ConfigCache.notification_spooling() == "local"


@pytest.mark.parametrize("value", ["off", "local", "remote", "both"])
def test_notification_spooling_explicit_string_wins_over_edition_default(
    monkeypatch: MonkeyPatch, value: Literal["off", "local", "remote", "both"]
) -> None:
    # Force community so its "off" default is different from any non-"off" value
    # and we can tell the override took effect.
    monkeypatch.setattr(config, "notification_spool_to", None)
    monkeypatch.setattr(config, "notification_spooling", value)
    monkeypatch.setattr(cmk_version, "edition", lambda _omd_root: Edition.COMMUNITY)
    assert ConfigCache.notification_spooling() == value


def test_notification_spooling_spool_to_with_also_local_returns_both(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "notification_spool_to", ("remote.example", 6555, True))
    monkeypatch.setattr(config, "notification_spooling", None)
    assert ConfigCache.notification_spooling() == "both"


def test_notification_spooling_spool_to_without_also_local_returns_remote(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "notification_spool_to", ("remote.example", 6555, False))
    monkeypatch.setattr(config, "notification_spooling", None)
    assert ConfigCache.notification_spooling() == "remote"


def test_notification_spooling_legacy_boolean_falls_through_to_edition_default(
    monkeypatch: MonkeyPatch,
) -> None:
    # Legacy: `notification_spooling = True/False` (non-string) should fall
    # through the `isinstance(..., str)` branch to the edition-aware default.
    monkeypatch.setattr(config, "notification_spool_to", None)
    monkeypatch.setattr(config, "notification_spooling", True)
    monkeypatch.setattr(cmk_version, "edition", lambda _omd_root: Edition.COMMUNITY)
    assert ConfigCache.notification_spooling() == "off"
