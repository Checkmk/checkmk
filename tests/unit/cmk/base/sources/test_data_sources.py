#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="type-arg"

# TODO: Move this file into the cmk-check-engine package. First eliminate dependency on testlib.

import os
import socket
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Never

import pytest

from cmk.base.config import LoadingResult
from cmk.base.modes.check_mk import handle_fetcher_options
from cmk.ccc.exceptions import OnError
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.checkengine.fetcher_abc import FetcherError, Mode
from cmk.checkengine.fetchers.piggyback import PiggybackFetcher
from cmk.checkengine.fetchers.program import ProgramFetcher
from cmk.checkengine.fetchers.snmp import NoSelectedSNMPSections, SNMPFetcher, SNMPFetcherConfig
from cmk.checkengine.fetchers.tcp import TCPFetcher, TLSConfig
from cmk.checkengine.filecache import (
    AgentFileCache,
    FileCache,
    FileCacheOptions,
    MaxAge,
    SNMPFileCache,
)
from cmk.checkengine.helper_interface import AgentRawData, FetcherType
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.checkengine.snmplib import SNMPRawData
from cmk.checkengine.source_abc import Source
from cmk.checkengine.source_builder import SourceBuilder
from cmk.checkengine.sources._sources import (
    MissingIPSource,
    PiggybackSource,
    ProgramSource,
    SpecialAgentSource,
)
from cmk.ruleset_matcher.matcher import RuleSpec
from cmk.ruleset_matcher.tags import TagGroupID, TagID
from cmk.server_side_calls_backend import SpecialAgentCommandLine
from cmk.utils.ip_lookup import IPStackConfig
from tests.testlib.unit.base_configuration_scenario import Scenario


class _Default:
    """Distinguishes "caller said nothing" from "caller said None"."""


_DEFAULT = _Default()


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
    host_address: HostAddress | None | _Default = _DEFAULT,
    ip_stack_config: IPStackConfig = IPStackConfig.IPv4,
    simulation_mode: bool = True,
    file_cache_options: FileCacheOptions = FileCacheOptions(),
) -> Sequence[Source]:
    # Too many arguments to this function.  Let's wrap it to make it easier
    # to test.
    ipaddress = HostAddress("127.0.0.1")
    # Only the address the sources are built for varies; everything else keeps
    # the resolvable one so a test changes one thing at a time.  None is a
    # meaningful value here ("no address at all"), hence the sentinel.
    host_address = ipaddress if isinstance(host_address, _Default) else host_address
    ip_family: Literal[socket.AddressFamily.AF_INET] = socket.AddressFamily.AF_INET
    config_cache = loading_result.config_cache
    return SourceBuilder(
        AgentBasedPlugins.empty(),
        hostname,
        ip_family,
        host_address,
        ip_stack_config,
        source_config=config_cache.make_source_config(
            config_cache.make_service_configurer({}, lambda *a: ""),  # noqa: ARG005
            ip_lookup=lambda *a: ipaddress,  # noqa: ARG005
            service_name_config=lambda *a: "",  # noqa: ARG005
            enforced_services_table=lambda hn: {},  # noqa: ARG005
            snmp_fetcher_config=SNMPFetcherConfig(
                on_error=OnError.RAISE,
                missing_sys_description=lambda host_name: False,  # noqa: ARG005
                selected_sections=NoSelectedSNMPSections(),
                backend_override=None,
                base_path=Path("/"),
                relative_stored_walk_path=tmp_path,
                relative_walk_cache_path=tmp_path,
                relative_section_cache_path=Path("dev/null"),
                caching_config=lambda host_name: {},  # noqa: ARG005
            ),
        ),
        simulation_mode=simulation_mode,
        file_cache_options=file_cache_options,
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
                ip_address_of=lambda *a: ipaddress,  # noqa: ARG005
                executable_finder=lambda name, module: "/yolo/bin/hurra",  # noqa: ARG005
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


@pytest.mark.parametrize("fallback", (HostAddress("0.0.0.0"), HostAddress("::")))
def test_agent_host_with_fallback_address_has_no_tcp_source(
    fallback: HostAddress, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """0.0.0.0 and :: mean "no address", so the agent must not be fetched.

    Without this the TCP fetcher would connect to the local system instead of
    the host, because Linux routes the unspecified address there.
    """
    hostname = HostName("agent-host")

    ts = Scenario()
    ts.add_host(hostname)
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source)
        for source in _make_sources(
            hostname, loading_result, tmp_path=tmp_path, host_address=fallback
        )
    ] == [MissingIPSource, PiggybackSource]


@pytest.mark.parametrize("fallback", (HostAddress("0.0.0.0"), HostAddress("::")))
def test_special_agent_with_fallback_address_reports_missing_ip(
    fallback: HostAddress, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A special agent may use $HOSTADDRESS$, and we cannot tell whether it does.

    The refusal keeps the agent's own ident so it stays visible per agent
    instead of the source silently disappearing.
    """
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
    sources = _make_sources(hostname, loading_result, tmp_path=tmp_path, host_address=fallback)
    assert sorted(
        source.source_info().ident for source in sources if isinstance(source, MissingIPSource)
    ) == ["special_jolokia", "special_mqtt"]


def test_no_ip_host_with_special_agent_still_runs_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A NO_IP host is configured to have no address at all.

    Its address-independent special agents are legitimate and must keep
    running -- unlike a host that asked for an IP family and has no usable
    address.
    """
    hostname = HostName("no-ip-host")
    tags = {TagGroupID("agent"): TagID("special-agents")}

    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    loading_result = ts.apply(monkeypatch)

    sources = _make_sources(
        hostname,
        loading_result,
        tmp_path=tmp_path,
        host_address=None,
        ip_stack_config=IPStackConfig.NO_IP,
        special_agent_command_lines=[("my_agent", SpecialAgentCommandLine("--go"))],
    )
    assert [
        source.fetcher().cmdline for source in sources if isinstance(source, SpecialAgentSource)
    ] == ["--go"]


@pytest.mark.parametrize(
    "program",
    (
        "/bin/get_data --host $HOSTADDRESS$",
        "/bin/get_data --host $_HOSTADDRESS_4$",
        "/bin/get_data --host $HOST_ADDRESS_6$",
        "/bin/get_data --host <IP>",
    ),
)
def test_datasource_program_using_the_address_is_refused(
    program: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Expanding these would run the program against the local system."""
    hostname = HostName("program-host")

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset("datasource_programs", [_dummy_rule_spec(hostname, program)])
    loading_result = ts.apply(monkeypatch)
    assert [
        type(source)
        for source in _make_sources(
            hostname,
            loading_result,
            tmp_path=tmp_path,
            host_address=HostAddress("0.0.0.0"),
        )
    ] == [MissingIPSource, PiggybackSource]


def test_datasource_program_not_using_the_address_still_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The command line is the user's own, and this one cannot reach the host
    through the unspecified address because it never mentions it."""
    hostname = HostName("program-host")

    ts = Scenario()
    ts.add_host(hostname)
    ts.set_ruleset("datasource_programs", [_dummy_rule_spec(hostname, "/bin/cat /var/lib/dump")])
    loading_result = ts.apply(monkeypatch)
    assert [
        source.fetcher().cmdline
        for source in _make_sources(
            hostname,
            loading_result,
            tmp_path=tmp_path,
            host_address=HostAddress("0.0.0.0"),
        )
        if isinstance(source, ProgramSource)
    ] == ["/bin/cat /var/lib/dump"]


_NO_TCP_HOSTS = pytest.mark.parametrize(
    "tags, special_agent_command_lines, fetcher_types",
    [
        pytest.param(
            {TagGroupID("agent"): TagID("cmk-agent"), TagGroupID("snmp_ds"): TagID("snmp-v2")},
            None,
            {FetcherType.TCP, FetcherType.SNMP},
            id="agent-and-snmp",
        ),
        pytest.param(
            {TagGroupID("agent"): TagID("special-agents")},
            [("my_agent", SpecialAgentCommandLine(""))],
            {FetcherType.SPECIAL_AGENT},
            id="special-agent",
        ),
    ],
)


def _no_tcp_file_caches(
    tags: dict[TagGroupID, TagID],
    special_agent_command_lines: Sequence[tuple[str, SpecialAgentCommandLine]] | None,
    fetcher_types: set[FetcherType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Sequence[FileCache[AgentRawData] | FileCache[SNMPRawData]]:
    hostname = HostName("no-tcp-host")
    ts = Scenario()
    ts.add_host(hostname, tags=tags)
    # `cmk -I <host>` defaults to not using the cache at all.
    file_cache_options = handle_fetcher_options(
        {"no-tcp": True}, defaults=FileCacheOptions(disabled=True)
    )
    sources = [
        source
        for source in _make_sources(
            hostname,
            ts.apply(monkeypatch),
            tmp_path=tmp_path,
            special_agent_command_lines=special_agent_command_lines,
            simulation_mode=False,
            file_cache_options=file_cache_options,
        )
        if not isinstance(source, PiggybackSource)
    ]
    assert {source.source_info().fetcher_type for source in sources} == fetcher_types
    return [
        source.file_cache(simulation=False, file_cache_options=file_cache_options)
        for source in sources
    ]


@_NO_TCP_HOSTS
def test_no_tcp_reads_outdated_cache_files(
    tags: dict[TagGroupID, TagID],
    special_agent_command_lines: Sequence[tuple[str, SpecialAgentCommandLine]] | None,
    fetcher_types: set[FetcherType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    file_caches = _no_tcp_file_caches(
        tags, special_agent_command_lines, fetcher_types, monkeypatch, tmp_path
    )
    for file_cache in file_caches:
        if isinstance(file_cache, SNMPFileCache):
            file_cache.write({}, Mode.DISCOVERY)
        elif isinstance(file_cache, AgentFileCache):
            file_cache.write(AgentRawData(b"<<<cached>>>"), Mode.DISCOVERY)
    a_day_ago = time.time() - 86400
    for path in tmp_path.rglob("*"):
        if path.is_file():
            os.utime(path, (a_day_ago, a_day_ago))

    for file_cache in file_caches:
        assert file_cache.read(Mode.DISCOVERY) is not None


@_NO_TCP_HOSTS
def test_no_tcp_does_not_fetch_without_cache_files(
    tags: dict[TagGroupID, TagID],
    special_agent_command_lines: Sequence[tuple[str, SpecialAgentCommandLine]] | None,
    fetcher_types: set[FetcherType],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    for file_cache in _no_tcp_file_caches(
        tags, special_agent_command_lines, fetcher_types, monkeypatch, tmp_path
    ):
        with pytest.raises(FetcherError, match="No cached data available"):
            file_cache.read(Mode.DISCOVERY)
