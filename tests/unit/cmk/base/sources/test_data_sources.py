#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Literal

import pytest

from tests.testlib.unit.base_configuration_scenario import Scenario

from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName

from cmk.utils.ip_lookup import IPStackConfig
from cmk.utils.rulesets.ruleset_matcher import RuleSpec
from cmk.utils.tags import TagGroupID, TagID

from cmk.fetchers import (
    PiggybackFetcher,
    ProgramFetcher,
    SNMPFetcher,
    SNMPScanConfig,
    TCPFetcher,
    TLSConfig,
)
from cmk.fetchers.filecache import FileCacheOptions, MaxAge

from cmk.checkengine.parser import NO_SELECTION
from cmk.checkengine.plugins import AgentBasedPlugins

from cmk.base.config import ConfigCache
from cmk.base.sources import make_sources, SNMPFetcherConfig, Source


def _dummy_rule_spec(host_name: HostName, value: Mapping[str, object] | str) -> RuleSpec:
    return {
        "condition": {
            "host_name": [host_name],
        },
        "id": "02",
        "value": value,
    }


def _make_sources(
    hostname: HostName,
    config_cache: ConfigCache,
    *,
    tmp_path: Path,
) -> Sequence[Source]:
    # Too many arguments to this function.  Let's wrap it to make it easier
    # to test.
    ipaddress = HostAddress("127.0.0.1")
    ip_family: Literal[socket.AddressFamily.AF_INET] = socket.AddressFamily.AF_INET
    return make_sources(
        AgentBasedPlugins.empty(),
        hostname,
        ip_family,
        ipaddress,
        IPStackConfig.IPv4,
        fetcher_factory=config_cache.fetcher_factory(
            config_cache.make_service_configurer(
                {}, config_cache.make_passive_service_name_config()
            ),
            ip_lookup=lambda *a: ipaddress,
        ),
        snmp_fetcher_config=SNMPFetcherConfig(
            scan_config=SNMPScanConfig(
                on_error=OnError.RAISE,
                missing_sys_description=False,
                oid_cache_dir=tmp_path,
            ),
            selected_sections=NO_SELECTION,
            backend_override=None,
            stored_walk_path=tmp_path,
            walk_cache_path=tmp_path,
        ),
        is_cluster=False,
        simulation_mode=True,
        file_cache_options=FileCacheOptions(),
        file_cache_max_age=MaxAge.zero(),
        snmp_backend=config_cache.get_snmp_backend(hostname),
        file_cache_path=tmp_path,
        tcp_cache_path=tmp_path,
        tls_config=TLSConfig(
            cas_dir=tmp_path,
            ca_store=tmp_path,
            site_crt=tmp_path,
        ),
        computed_datasources=config_cache.computed_datasources(hostname),
        datasource_programs=config_cache.datasource_programs(hostname),
        tag_list=config_cache.host_tags.tag_list(hostname),
        management_ip=ipaddress,
        management_protocol=config_cache.management_protocol(hostname),
        special_agent_command_lines=config_cache.special_agent_command_lines(
            hostname,
            ip_family,
            ipaddress,
            password_store_file=Path("/pw/store"),
            passwords={},
            ip_address_of=lambda *a: ipaddress,
        ),
        agent_connection_mode=config_cache.agent_connection_mode(hostname),
        check_mk_check_interval=config_cache.check_mk_check_interval(hostname),
    )


def test_ping_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("ping-host")
    tags = {TagGroupID("agent"): TagID("no-agent")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [PiggybackFetcher]


def test_agent_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("agent-host")

    ts = Scenario()
    ts.add_host(hostname)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [TCPFetcher, PiggybackFetcher]


def test_agent_host_with_special_agents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("agent-host")

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset_bundle(
        "special_agents",
        {
            "jolokia": [_dummy_rule_spec(hostname, {})],
            "mqtt": [_dummy_rule_spec(hostname, {})],
        },
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [ProgramFetcher, ProgramFetcher, PiggybackFetcher]


@pytest.mark.parametrize("snmp_ds", (TagID("snmp-v1"), TagID("snmp-v2")))
def test_snmp_host(snmp_ds: TagID, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("snmp-host")
    tags = {TagGroupID("agent"): TagID("no-agent"), TagGroupID("snmp_ds"): snmp_ds}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [SNMPFetcher, PiggybackFetcher]


def test_dual_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("dual-host")
    tags = {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [TCPFetcher, SNMPFetcher, PiggybackFetcher]


def test_all_agents_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("all-agents-host")
    tags = {TagGroupID("agent"): TagID("all-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_ruleset(
        "datasource_programs",
        [_dummy_rule_spec(hostname, "")],
    )
    ts.set_option(
        "special_agents",
        {"jolokia": [_dummy_rule_spec(hostname, {})]},
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [ProgramFetcher, ProgramFetcher, PiggybackFetcher]


def test_special_agents_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("all-special-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    ts.set_option(
        "special_agents",
        {"jolokia": [_dummy_rule_spec(hostname, {})]},
    )
    config_cache = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, config_cache, tmp_path=tmp_path)
    ] == [ProgramFetcher, PiggybackFetcher]
