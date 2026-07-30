#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# TODO: Move this file into the cmk-check-engine package. First eliminate dependency on testlib.

import socket
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Never

import pytest

from cmk.base.config import LoadingResult
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetchers.piggyback import PiggybackFetcher
from cmk.checkengine.fetchers.program import ProgramFetcher
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcher, SNMPFetcherConfig
from cmk.checkengine.fetchers.tcp import TCPFetcher, TLSConfig
from cmk.checkengine.filecache import FileCacheOptions, MaxAge
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.source_abc import Source
from cmk.checkengine.source_builder import SourceBuilder
from cmk.checkengine.sources._sources import SpecialAgentSource
from cmk.ruleset_matcher.matcher import RuleSpec
from cmk.ruleset_matcher.tags import TagGroupID, TagID
from cmk.server_side_calls_backend import SpecialAgentCommandLine
from cmk.utils.ip_lookup import IPStackConfig
from tests.testlib.unit.base_configuration_scenario import Scenario


@dataclass(frozen=True)
class _SecretsConfig:
    path: Path
    secrets: Mapping[str, Never]


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
    loading_result: LoadingResult,
    *,
    tmp_path: Path,
    special_agent_command_lines: Sequence[tuple[str, SpecialAgentCommandLine]] | None = None,
) -> Sequence[Source]:
    # Too many arguments to this function.  Let's wrap it to make it easier
    # to test.
    ipaddress = HostAddress("127.0.0.1")
    ip_family: Literal[socket.AddressFamily.AF_INET] = socket.AddressFamily.AF_INET
    config_cache = loading_result.config_cache
    return SourceBuilder(
        AgentBasedPlugins.empty(),
        hostname,
        ip_family,
        ipaddress,
        IPStackConfig.IPv4,
        source_config=config_cache.make_source_config(
            config_cache.make_service_configurer({}, lambda *a: ""),
            ip_lookup=lambda *a: ipaddress,
            service_name_config=lambda *a: "",
            enforced_services_table=lambda hn: {},
            snmp_fetcher_config=SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=lambda host_name: False,
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=Path("/"),
                relative_stored_walk_path=tmp_path,
                relative_walk_cache_path=tmp_path,
                relative_section_cache_path=Path("dev/null"),
                caching_config=lambda host_name: {},
            ),
        ),
        simulation_mode=True,
        file_cache_options=FileCacheOptions(),
        file_cache_max_age=MaxAge.zero(),
        snmp_backend=config_cache.get_snmp_backend(hostname),
        file_cache_path_base=Path("/"),
        file_cache_path_relative=tmp_path,
        tcp_cache_path_relative=tmp_path,
        tls_config=TLSConfig(
            cas_dir=tmp_path,
            ca_store=tmp_path,
            site_crt=tmp_path,
        ),
        computed_datasources=config_cache.computed_datasources(hostname),
        datasource_programs=config_cache.datasource_programs(hostname),
        tag_list=loading_result.host_tags.tag_list(hostname),
        management_ip=ipaddress,
        management_protocol=config_cache.management_protocol(hostname),
        special_agent_command_lines=(
            config_cache.special_agent_command_lines(
                hostname,
                ip_family,
                ipaddress,
                secrets_config=_SecretsConfig(path=Path("/pw/store"), secrets={}),
                ip_address_of=lambda *a: ipaddress,
                executable_finder=lambda name, module: "/yolo/bin/hurra",
                for_relay=False,
            )
            if special_agent_command_lines is None
            else special_agent_command_lines
        ),
        is_pull_host=config_cache.is_pull_host(hostname),
        check_mk_check_interval=config_cache.check_mk_check_interval(hostname),
        metrics_association=config_cache.metrics_association(hostname),
        omd_root=Path("/"),
    ).sources


def test_ping_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("ping-host")
    tags = {TagGroupID("agent"): TagID("no-agent")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
    ] == [PiggybackFetcher]


def test_agent_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("agent-host")

    ts = Scenario()
    ts.add_host(hostname)
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
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
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
    ] == [ProgramFetcher, ProgramFetcher, PiggybackFetcher]


@pytest.mark.parametrize("snmp_ds", (TagID("snmp-v1"), TagID("snmp-v2")))
def test_snmp_host(snmp_ds: TagID, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("snmp-host")
    tags = {TagGroupID("agent"): TagID("no-agent"), TagGroupID("snmp_ds"): snmp_ds}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
    ] == [SNMPFetcher, PiggybackFetcher]


def test_dual_host(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    hostname = HostName("dual-host")
    tags = {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
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
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
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
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source.fetcher())
        for source in _make_sources(hostname, loading_result, tmp_path=tmp_path)
    ] == [ProgramFetcher, PiggybackFetcher]


def test_special_agent_multiple_command_lines_same_agent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hostname = HostName("all-special-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)

    sources = _make_sources(
        hostname,
        loading_result,
        tmp_path=tmp_path,
        special_agent_command_lines=[
            ("my_agent", SpecialAgentCommandLine("--instance one")),
            ("my_agent", SpecialAgentCommandLine("--instance two")),
        ],
    )

    special_agents = [source for source in sources if isinstance(source, SpecialAgentSource)]
    assert len(special_agents) == 2

    # Every command line is executed ...
    assert sorted(source.fetcher().cmdline for source in special_agents) == [
        "--instance one",
        "--instance two",
    ]

    # ... with a unique ident that carries the index ...
    idents = [source.source_info().ident for source in special_agents]
    assert sorted(idents) == ["special_my_agent_0", "special_my_agent_1"]

    # ... and therefore with independent file caches.
    cache_paths = {
        source.file_cache(
            simulation=True, file_cache_options=FileCacheOptions()
        ).relative_path_template
        for source in special_agents
    }
    assert len(cache_paths) == 2


def test_special_agent_single_command_line_has_no_index(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A single command line keeps the plain, index-less ident for backwards
    # compatibility (cache paths must not change for the common case).
    hostname = HostName("all-special-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)

    sources = _make_sources(
        hostname,
        loading_result,
        tmp_path=tmp_path,
        special_agent_command_lines=[
            ("my_agent", SpecialAgentCommandLine("--instance one")),
        ],
    )

    special_agents = [source for source in sources if isinstance(source, SpecialAgentSource)]
    assert [source.source_info().ident for source in special_agents] == ["special_my_agent"]


def test_special_agent_multiple_agents_keep_distinct_idents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    hostname = HostName("all-special-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)

    sources = _make_sources(
        hostname,
        loading_result,
        tmp_path=tmp_path,
        special_agent_command_lines=[
            ("agent_a", SpecialAgentCommandLine("--a1")),
            ("agent_a", SpecialAgentCommandLine("--a2")),
            ("agent_b", SpecialAgentCommandLine("--b1")),
        ],
    )

    idents = sorted(
        source.source_info().ident for source in sources if isinstance(source, SpecialAgentSource)
    )
    assert idents == ["special_agent_a_0", "special_agent_a_1", "special_agent_b"]
